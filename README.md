# Nutrizzi App

The appwill use a table detection model to determine the location of the nutritional information table entered by the user, either directly from the camera or the user's gallery. If the YOLOv8s model can determine the location of the table, the image will be cropped based on the location of the nutritional information. The image will then be processed using PP-OCRv3-rec OCR. The OCR results can be corrected if there are errors in the text recognition by the PP-OCRv3-rec model. The user will need to select the product category they entered. The nutritional information values ​​will then be evaluated, determining the maximum or minimum limits according to the BPOM guidelines for that category. The app can be accessed at the following link:  [https://nutrizziapplwfeljcukhgxk4rvdginl8.streamlit.app/](url).

## Installation
Clone the repository with the git clone code as in the following code:
```
git clone https://github.com/Snasset/nutrizzi_app.git
```

After the repository cloning process is complete, move to the directory and install the libraries required for this app using the following code:

```
cd nutrizzi_app 
pip install -r requirements.txt
```


Finally, the appcan be run by typing and running the following code in the terminal:

```
streamlit run app.py 
```
