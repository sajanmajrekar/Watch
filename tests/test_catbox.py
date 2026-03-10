import subprocess

def upload_to_catbox(file_path):
    command = [
        "curl", "-F", "reqtype=fileupload",
        "-F", f"fileToUpload=@{file_path}",
        "https://catbox.moe/user/api.php"
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout.strip()

# Create a dummy image
from PIL import Image
img = Image.new('RGB', (100, 100), color = 'red')
img.save('test_upload.jpg')

url = upload_to_catbox('test_upload.jpg')
print("Uploaded URL:", url)
