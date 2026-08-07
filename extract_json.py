import openpyxl
import json

file_path = r'c:\Users\AYENA Gédéon\OneDrive\Desktop\SEIFAX\Frontend\assets\Calculateur_Notes.xlsx'

try:
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb['Feuil1']
    
    data = []
    # Start at row 7
    for row in ws.iter_rows(min_row=7, min_col=5, max_col=17, values_only=True):
        if not row[0] or row[0] == 'Matières': continue
        matiere = row[0]
        
        # Check if it's a category header
        if "Matières Principales" in matiere or "Matières Secondaires" in matiere:
            data.append({"type": "category", "name": matiere})
            continue
            
        int_coef = row[1] or 0
        comp_coef = row[3] or 0
        ex_coef = row[5] or 0
        tp_coef = row[7] or 0
        
        if int_coef == 0 and comp_coef == 0 and ex_coef == 0 and tp_coef == 0:
            continue
            
        data.append({
            "type": "subject",
            "name": matiere,
            "coefs": {
                "int": float(int_coef) if int_coef else 0,
                "comp": float(comp_coef) if comp_coef else 0,
                "ex": float(ex_coef) if ex_coef else 0,
                "tp": float(tp_coef) if tp_coef else 0
            }
        })
        
    with open('subjects_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Data extracted successfully to subjects_data.json")
except Exception as e:
    print(f"Error reading Excel file: {e}")
