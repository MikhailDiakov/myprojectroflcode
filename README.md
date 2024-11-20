# MyProjectRoflCode

### About  
A **prototype social network** built with Flask.  


### Installation  

1. **Clone the repository and configuration creation**:  
   ```bash
   git clone https://github.com/MikhailDiakov/myprojectroflcode.git
   cd myprojectroflcode
   mkdir instance
   touch instance/config.py

   - FILE THIS!!!
   class Config:
      SECRET_KEY = 'your-secret-key'
      SQLALCHEMY_DATABASE_URI = 'sqlite:///iambored.db'
      SQLALCHEMY_TRACK_MODIFICATIONS = False
   CHANGE SECRET_KEY!!!
   ```

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
