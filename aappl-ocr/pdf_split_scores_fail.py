import os
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from pypdf import PdfReader, PdfWriter
import requests
import io
import fitz  # PyMuPDF


desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop/Scores')
for path in ["/French/Darma-Hoover/Output"]:#,
                # "/French/Darma-Hoover/DarmaHoover AAPPL Scores.pdf",
                # "/Mandarin/Huang/Huang AAPPL Scores.pdf",
                # "/Mandarin/Leonard/Leonard AAPPL Scores.pdf",
                # "/Mandarin/Yu/Yu AAPPL Scores.pdf",
                # "/Spanish/Colston/Colston AAPPL Scores.pdf",
                # "/Spanish/Dunn/Dunn AAPPL Scores.pdf",
                # "/Spanish/Gallardo/Gallardo AAPPL Scores.pdf",
                # "/Spanish/Mabene/Mabene AAPPL Scores.pdf",
                # "/Spanish/Mendez/Mendez AAPPL Scores.pdf",
                # "/Spanish/Perry/Perry AAPPL Scores.pdf",
                # "/Spanish/Rodriguez/Rodriguez AAPPL Scores.pdf",
                # "/Spanish/Sandels/Sandels AAPPL Scores.pdf"]:
        folder = desktop_path + "/" + path
        os.chdir(folder)
        files = os.listdir(folder)
        
        for file in files:
            #print(file)
            reader = PdfReader(file)
            if file.endswith("4.pdf"):
                print(file)
                
                # 1st approach: - doesn't work        
                for page_index, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text() or ""
                    except Exception as e:
                        print(f"Error extracting text from page {page_index + 1}: {e}")
                        text = ""

                    print(f"\n--- Page {page_index + 1}/{len(reader.pages)} ---")
                    print(text.strip())

                # 2nd approach: document information dictionary doesn't have any useful info
                # reader = PdfReader(file)
                # info = reader.metadata
                # if info:
                #     print("PDF Document Information:")
                #     for key, value in info.items():
                #         print(f"  {key}: {value}")
                # else:
                #     print("No document information found in this PDF.")

                # 3rd approch: Works but doesn't pick up text in drawings
                # try:
                # # Open the PDF file
                #     with fitz.open(file) as doc:
                #         # Iterate through each page
                #         for i, page in enumerate(doc):
                #             # Get the drawing commands
                #             drawings = page.get_drawings()
                #             if drawings:
                #                 print(f"--- Drawings on Page {i + 1} ---")
                #                 for drawing in drawings:
                #                     print(drawing)
                # except FileNotFoundError:
                #     print("Error: The specified PDF file was not found.")
                # except Exception as e:
                #     print(f"An error occurred: {e}")