import os
import logging
from pathlib import Path
from typing import Literal
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from image_generator import ImageGenerator
from gpt_service import GPTService

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = FastAPI()

# Function to be run as a background task.
# This is just a placeholder function for demonstration.
# In your application, this could be a function that generates an image.
def write_log(message: str):
    # Example of a time-consuming task: Writing a message to a file.
    # Replace this with the logic of your image generation task.
    with open("log.txt", "a") as file:
        file.write(f"{message}\n")

@app.get("/example")
async def example_endpoint(background_tasks: BackgroundTasks):
    # This endpoint demonstrates how to add a background task.
    # The `write_log` function will be executed after the response is sent.
    # Note: The task runs in the same process but does not block the response.
    background_tasks.add_task(write_log, "Example endpoint was visited")
    return {"message": "This is an example endpoint"}


IMAGE_DIR = Path(__file__).resolve().parent / "generated_images"
image_jobs = {}


# Define custom prompt fields and validation
class ImageRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=150)
    setting: str = Field(min_length=3, max_length=150)
    viewpoint: Literal["front", "side", "top", "isometric"] = "isometric"
    details: str = Field(default="", max_length=300)


# Build the image prompt from user input
def build_prompt(request: ImageRequest) -> str:
    prompt = f"A concept design of {request.subject} in {request.setting}, {request.viewpoint} view"
    if request.details.strip():
        prompt += f", featuring {request.details.strip()}"
    return prompt


# Check the prompt for profanity using the provided GPT service
def check_profanity(prompt: str) -> bool:
    prompt_file = Path(__file__).resolve().parent / "profanity_prompt.txt"
    instructions = prompt_file.read_text(encoding="utf-8")
    service = GPTService(os.environ["OPENAI_API_KEY"], instructions)
    return service.contains_profanity(prompt)


# Generate and save the image in the background
def gen_image_task(image_id: str, prompt: str):
    try:
        generator = ImageGenerator(os.environ["STABILITY_API_KEY"])
        image_data = generator.generate_image(prompt)
        if not image_data:
            raise ValueError("Image generator returned no image")

        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        (IMAGE_DIR / f"{image_id}.png").write_bytes(image_data)
        image_jobs[image_id] = "ready"
    except Exception:
        image_jobs[image_id] = "failed"
        logging.exception("Image generation failed for %s", image_id)


# Accept image requests and start background generation
@app.post("/images", status_code=202)
async def create_image(request: ImageRequest, background_tasks: BackgroundTasks):
    if not os.getenv("STABILITY_API_KEY"):
        raise HTTPException(status_code=503, detail="Stability API key is missing")
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="OpenAI API key is missing")

    prompt = build_prompt(request)
    try:
        flagged = await run_in_threadpool(check_profanity, prompt)
    except Exception as exc:
        logging.exception("Profanity check failed")
        raise HTTPException(status_code=503, detail="Profanity check unavailable") from exc

    if flagged:
        raise HTTPException(status_code=400, detail="Prompt contains profanity")

    image_id = uuid4().hex
    image_jobs[image_id] = "processing"
    background_tasks.add_task(gen_image_task, image_id, prompt)
    return {"image_id": image_id, "status": "processing", "image_url": f"/image/{image_id}"}


# Retrieve generated images and handle different image statuses
@app.get("/image/{image_id}")
async def get_image(image_id: str):
    image_path = IMAGE_DIR / f"{image_id}.png"
    if image_path.is_file():
        return FileResponse(image_path, media_type="image/png")

    image_status = image_jobs.get(image_id)
    if image_status == "processing":
        return JSONResponse(status_code=202, content={"image_id": image_id, "status": "processing"})
    if image_status == "failed":
        return JSONResponse(status_code=500, content={"image_id": image_id, "status": "failed"})
    raise HTTPException(status_code=404, detail="Image not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)