import torch
from diffusers import AutoPipelineForText2Image

model_id = "stabilityai/sdxl-turbo"

device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.float32

pipe = AutoPipelineForText2Image.from_pretrained(
    model_id,
    torch_dtype=dtype,
    variant="fp16" if device == "cuda" else None,
)

pipe = pipe.to(device)

prompt = (
    "Educational illustration explaining the solar system, "
    "eight planets orbiting the sun, scientific textbook style, "
    "clear composition, colorful background"
)

image = pipe(
    prompt=prompt,
    num_inference_steps=2,
    guidance_scale=0.0,
    width=512,
    height=512,
).images[0]

image.save("illustration_test.png")
print("Image générée : illustration_test.png")