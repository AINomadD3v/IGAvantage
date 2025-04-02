import uiautomator2 as u2
from PIL import Image
import torch
from transformers import Blip2Processor, Blip2ForConditionalGeneration

# ---------- Step 1: Screenshot from device ----------
d = u2.connect()
screenshot_path = "reel_screenshot.jpg"
d.screenshot(screenshot_path)

# ---------- Step 2: Load BLIP-2 ----------
print("Loading BLIP-2 model...")
processor = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b")
model = Blip2ForConditionalGeneration.from_pretrained("Salesforce/blip2-opt-2.7b",
                                                      torch_dtype=torch.float16,
                                                      device_map="auto")

# ---------- Step 3: Generate Caption ----------
image = Image.open(screenshot_path).convert("RGB")
prompt = "Describe the image."
inputs = processor(images=image, text=prompt, return_tensors="pt").to("cuda", torch.float16)
output = model.generate(**inputs, max_new_tokens=50)
caption = processor.decode(output[0], skip_special_tokens=True)

print(f"Caption: {caption}")

# ---------- Step 4: Detect Woman ----------
keywords = ["woman", "girl", "female", "lady"]
if any(word in caption.lower() for word in keywords):
    print("✅ Woman detected in reel.")
else:
    print("❌ No woman detected — skip this reel.")

