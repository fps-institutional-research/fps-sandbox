import os
import re
import pandas as pd
from pypdf import PdfReader, PdfWriter
from pypdf import PageObject

path = os.path.join(os.path.expanduser('~'), 'Desktop')
for file in ["Scores/French/Satter/Satter AAPPL Scores.pdf",
                "Scores/French/Darma-Hoover/DarmaHoover AAPPL Scores.pdf",
                "Scores/Mandarin/Huang/Huang AAPPL Scores.pdf",
                "Scores/Mandarin/Leonard/Leonard AAPPL Scores.pdf",
                "Scores/Mandarin/Yu/Yu AAPPL Scores.pdf",
                "Scores/Spanish/Colston/Colston AAPPL Scores.pdf",
                "Scores/Spanish/Dunn/Dunn AAPPL Scores.pdf",
                "Scores/Spanish/Gallardo/Gallardo AAPPL Scores.pdf",
                "Scores/Spanish/Mabene/Mabene AAPPL Scores.pdf",
                "Scores/Spanish/Mendez/Mendez AAPPL Scores.pdf",
                "Scores/Spanish/Perry/Perry AAPPL Scores.pdf",
                "Scores/Spanish/Rodriguez/Rodriguez AAPPL Scores.pdf",
                "Scores/Spanish/Sandels/Sandels AAPPL Scores.pdf"]:
    
    # Define input directory
        pdf_input_path = path + "/" + file
        print("Input: " + f"{pdf_input_path}")
    # Define output directory
        pdf_output_folder = "/".join(pdf_input_path.split('/')[:7]) + "/Output"
        print("Output: " + pdf_output_folder)
    # Create output directory if it doesn't exist    
        if not os.path.exists(pdf_output_folder):
            os.makedirs(pdf_output_folder)
    # Create PDF reader
        pdf_reader = PdfReader(pdf_input_path)
        total_pages = len(pdf_reader.pages)
        print(f"Total pages: {total_pages}")

    #Split and save each page as a separate PDF
        for i in range(total_pages):
            pdf_writer = PdfWriter()
            pdf_writer.add_page(pdf_reader.pages[i])
            output_filename = os.path.splitext(os.path.basename(pdf_input_path))[0] + f"_page_{i+1}.pdf"
            output_path = os.path.join(pdf_output_folder, output_filename)
            with open(output_path, "wb") as out_f:
                pdf_writer.write(out_f)
            print(f"Saved: {output_path}")