import openpyxl

file_path = r'c:\Users\AYENA Gédéon\OneDrive\Desktop\SEIFAX\Frontend\assets\Calculateur_Notes.xlsx'

try:
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb['Feuil1']
    
    for i, row in enumerate(ws.iter_rows(min_row=4, max_row=35, min_col=5, max_col=18, values_only=True)):
        print(row)
                
except Exception as e:
    print(f"Error reading Excel file: {e}")
