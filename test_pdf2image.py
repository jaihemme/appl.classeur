# Source - https://stackoverflow.com/a/65236139
# Posted by Rajkumar, modified by community. See post 'Timeline' for change history
# Retrieved 2026-04-28, License - CC BY-SA 4.0

from pdf2image import convert_from_path
images = convert_from_path("mypdf.pdf", 500,poppler_path=r'C:\Program Files\poppler-0.68.0\bin')
for i, image in enumerate(images):
    fname = 'image'+str(i)+'.png'
    image.save(fname, "PNG")
