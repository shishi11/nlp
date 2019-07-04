from PIL import Image
import pytesseract
img='./resources/img/58.JPG'


text=pytesseract.image_to_string(Image.open(img),lang='chi_sim')
print(text)


from cnocr import CnOcr
ocr = CnOcr()
res = ocr.ocr(img)
print("Predicted Chars:", res)