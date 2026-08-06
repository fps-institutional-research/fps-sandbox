import easyocr
import pytesseract
import fitz  # PyMuPDF
import numpy as np
import os
import shutil
import re
from PIL import Image


desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop/Scores')
student_list = [] #Keep track of list of files
for path in ["/French/Darma-Hoover/Output",
             "/French/Satter/Output",
             "/Mandarin/Huang/Output",
             "/Mandarin/Leonard/Output",
             "/Mandarin/Yu/Output",
             "/Spanish/Colston/Output",
             "/Spanish/Dunn/Output",
             "/Spanish/Gallardo/Output",
             "/Spanish/Mabene/Output",
             "/Spanish/Mendez/Output",
             "/Spanish/Perry/Output",
             "/Spanish/Rodriguez/Output",
             "/Spanish/Sandels/Output"]:
        folder = desktop_path + "/" + path
        os.chdir(folder)
        files = os.listdir(folder)
        if '.DS_Store' in files:
            files.remove('.DS_Store') # Remove .DS_Store if it exists
        # --- Step 1: List all PDF files in the directory ---
        for index, file in enumerate(files):
            # --- Loop through files ---
            if file.endswith(".pdf"):
                index+=1 # Start index at 1 instead of 0
                print(file)
                # --- Step 2: Open the PDF and convert pages to images with PyMuPDF ---
                print("Converting PDF pages to images using PyMuPDF...")
                doc = fitz.open(file, filetype="pdf")
                images = []
                page = doc.load_page(0) # Load the first page (0-indexed)
                # --- Step 3: Render page to a pixmap (an image representation) ---
                pix = page.get_pixmap()
                # --- Step 4: Convert the pixmap to a PIL Image for Pytesseract (pix.samples attribute contains the image data as bytes) ---
                mode = "RGB" if pix.n == 3 else "RGBA"
                img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
                images.append(img)
                print(f"Successfully converted {file} to {len(images)} image(s).")
                doc.close()

                # --- Step 5: Perform OCR on each image ---
                extracted_text = []
                student_info = ""
                for i, image in enumerate(images):
                    print(f"Performing OCR on page {i + 1}...")
                    
                    # Use Pytesseract to detect and read text from the image
                    text = pytesseract.image_to_string(image)
                    
                    # Append the extracted text to the list
                    extracted_text.append(text)
                    #print(f"--- Text from Page {i + 1} ---")

                    # Extract Student Name/ID
                    match = re.search(r"AAPPL Score Report\s*(.*?)\s*Francis Parker School", text, re.DOTALL)
                    if match:
                        student_info = match.group(1).strip().lstrip("'").lstrip("‘").strip()
                        print("Found student info: " + student_info)
                        # Remove unwanted labels if they exist
                        for label in ["Student Name/ID:","Student Name/1D:"]:
                            if label in student_info:
                                student_info = student_info.replace(label, "").strip().lstrip("'").lstrip("‘").strip()
                        # Remove anything after the first occurrence of 7 consecutive digits
                        match_digits = re.search(r"\d{7}", student_info)
                        student_info = student_info[:match_digits.start()+7].strip() #Change 7 to -1 to get student name only
                        # Replace slashes with dashes    
                        student_info = student_info.replace("/", " - ").title()
                        # print(f"Extracted Student Name/ID: {student_info}")
                        student_list.append(f"{index} - {student_info}")
                    else:
                        print("Student Name/ID not found between markers.")
                print(f"Extracted Student Name - ID: {student_info}")
                # Rename the file & iterate to next file!
                #os.rename(file, f"{index} - {student_info}.pdf")
                # Create output directory if it doesn't exist 
                output_folder = "/".join(folder.split('/')[:-1]) + "/Renamed"
                if not os.path.exists(output_folder):
                    os.makedirs(output_folder)
                shutil.copy2(f"{folder}/{file}", f"{output_folder}/{index} - {student_info}.pdf")
                print(f"Renamed {file} to {index} - {student_info}.pdf")
                # Write out list of students to base directory for bulk upload
            else:
                print(f"Skipping {file} because it is not a PDF")

# Create output directory if it doesn't exist   

output_txt = desktop_path + "/Students List.txt"
try:
    with open(output_txt,'x') as f:
        for item in student_list:
            f.write(f"{item}\n")
except FileExistsError:
    print(f"File '{output_txt}' arleady exists. No action taken.")