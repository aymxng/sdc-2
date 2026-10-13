### Project Description: Building a FastAPI Application with Stable Diffusion Image Generation

**Objective**: Develop a FastAPI application from scratch that integrates the Stable Diffusion model, provided by Stability AI for custom image generation. You will create an asynchronous API that accepts unique prompts, processes them using Stable Diffusion, and generates corresponding images.

#### Background:
- Stable Diffusion is a powerful AI model capable of creating detailed images from textual descriptions.
- For now we'll simply integrate their sdk and access the model using their SaaS offering.
- Your task is to understand how to effectively utilize a ml model in a FastAPI context.

#### Resources Provided:
- Access to the `ImageGenerator` API that uses Stable Diffusion.
- A GPT-Service Implementation + API for optional profanity checking.
- An API key for the `ImageGenerator` service.
- Documentation on Stable Diffusion and its prompt-handling capabilities.

#### Key Tasks and Requirements:
1. **Set Up a FastAPI Project**:
   - Initialize a new FastAPI application.
   - Install necessary dependencies, including libraries for interacting with the `ImageGenerator` service.

2. **Custom Prompt Development**:
   - Design a unique prompt structure that users can utilize your own image requirements.

3. **Asynchronous Image Generation Endpoint (`/images`)**:
   - Create an endpoint to accept image generation requests.
   - Implement asynchronous processing using FastAPI's `BackgroundTasks`.
   - Optional: use redis queue

4. **Background Task for Image Generation (`gen_image_task`)**:
   - Code a function that uses the `ImageGenerator` with custom prompts to generate images.
   - Handle image saving and retrieval.

5. **Image Retrieval Endpoint (`/image/{image_id}`)**:
   - Develop an endpoint for users to retrieve their generated images using an image ID.
   - Implement appropriate responses for different image statuses (e.g., processing, ready, not found).

#### Deliverables:
- Complete source code of the FastAPI application.
- A README or documentation detailing the API usage, setup instructions, and any important decisions made during development.

#### Evaluation Criteria:
- Functionality and correctness of the FastAPI application in an async way.
- Effective integration of the Stable Diffusion model.
- Creativity and utility of the custom prompt system.

#### Tips:
- Start with a basic FastAPI setup and gradually integrate the image generation features.

This project is an excellent opportunity to demonstrate your skills in web API development, asynchronous programming, and AI model integration. Good luck!


## Implementation

This application generates concept sketches using Stable Diffusion through the provided ImageGenerator. It also uses the provided GPTService for optional profanity checking before starting image generation.

### Setup

Use Python 3.11 or newer and uv.

From the repository root:

```bash
cd assignment
uv sync --locked
```

Configure both `OPENAI_API_KEY` and `STABILITY_API_KEY` as environment variables or in a local `.env` file in the repository root.

API keys must not be included in the source code or committed to Git. The `.env` file is excluded through `.gitignore`.

Start the API:

```bash
uv run --locked uvicorn app:app --reload
```

Open http://127.0.0.1:8000/docs to use the API.

### Generate an image

Send a POST request to `/images` with a JSON body:

```json
{
  "subject": "A small solar-powered greenhouse",
  "setting": "a mountain village",
  "viewpoint": "isometric",
  "details": "glass panels, a wooden frame and rainwater collection"
}
```

The application combines these fields into a custom prompt. The provided ImageGenerator adds its sketch template and sends the request to Stability AI.

Before image generation, the prompt is checked for profanity using GPTService.

If the prompt passes the check, the endpoint starts a background task and returns HTTP 202 with an `image_id`, a processing status and an `image_url`.

Example response:

```json
{
  "image_id": "example123",
  "status": "processing",
  "image_url": "/image/example123"
}
```

### Profanity checking

The application uses the provided GPTService with `gpt-4o-mini` to check user prompts for inappropriate language.

The instructions for the GPT service are stored in `profanity_prompt.txt`.

If the prompt is flagged, the request is rejected with HTTP 400 and image generation is not started.

If the GPT service is unavailable, the endpoint returns HTTP 503.

### Retrieve an image

Send a GET request to `/image/{image_id}` using the returned ID.

Possible responses:

- 202: Image generation is still processing.
- 200: The generated PNG image is returned.
- 500: Image generation failed.
- 404: The image ID was not found.

Additional POST `/images` responses:

- 400: The prompt contains profanity.
- 422: Invalid request data.
- 503: An API key is missing or the profanity check is unavailable.

### Design decisions

FastAPI BackgroundTasks is used to run the synchronous image generator without making the initial HTTP request wait for image generation.

The GPT-based profanity check runs in a thread pool to avoid blocking the FastAPI event loop.

Image statuses are stored in memory, and generated PNG files are saved in `assignment/generated_images`.

This implementation uses a single server process. Running jobs are not preserved across restarts, but successfully saved PNG files remain available as long as the files are retained.

API keys are loaded from environment variables and are never hardcoded in the application.

Redis was not implemented because it is optional for this assignment.

### Testing

Run the existing automated tests from the assignment directory:

```bash
uv run --locked python -m unittest discover -s ../tests -v
```

The image generation and retrieval endpoints can also be tested using the interactive API documentation at `/docs`.

Background processing, image saving and retrieval can be tested with a mocked ImageGenerator without using Stability AI credits.

A successful live image generation request requires a valid Stability AI API key with sufficient balance.