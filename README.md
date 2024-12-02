# MyProjectRoflCode

### About  
A **prototype social network** built with Flask.  


### Installation  

1. **Clone the repository and configuration creation**:  
   ```bash
   git clone https://github.com/MikhailDiakov/myprojectroflcode.git
   cd myprojectroflcode
**Open the configuration file**:  
   Open `instance/config.py` and **replace** the `SECRET_KEY` line with your own key:
   - For Linux/Mac:  
     ```bash
     nano instance/config.py
     ```
   - For Windows:
     ```bash
     notepad instance/config.py
     ```

   To generate a new secret key:
   - For Linux/Mac:  
     ```bash
     python -c "import os; print(os.urandom(24))"
     ```
   - For Windows:  
     Open **Python** and run:
     ```python
     import os
     print(os.urandom(24))
     ```

   Copy the generated key and paste it in place of `'your-secret-key'`.

2. **Set up a virtual environment**:  
   - For Linux/Mac:  
     ```bash
     python -m venv venv  
     source venv/bin/activate  
     ```  
   - For Windows:  
     ```bash
     python -m venv venv  
     venv\Scripts\activate  
     ```  
      
3. **Install dependencies**:  
   ```bash
   pip install -r requirements.txt
   ```  

4. **Run the application**:  
   ```bash
   python run.py
   ```  

5. **Open in your browser**:  
   [http://127.0.0.1:5000](http://127.0.0.1:5000)  

---

### Author  
**[Mikhail Diakov](https://github.com/MikhailDiakov)**.  
