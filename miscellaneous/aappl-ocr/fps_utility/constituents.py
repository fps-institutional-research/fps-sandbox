import pandas as pd

class Student:
    def __init__(self, name):
        self.name = name #name should be in the format of "[First] [Last]"
        self.id = self._get_student_user_id()

    #Function to get a student's user ID based on the student entity
    def _get_student_user_id(self):
        self.df = pd.read_csv(
            "/Users/jshwisberg/Desktop/Data/Basic List/Student Information/Registered Students.csv",
            usecols=['Student User ID', 'First Name', 'Last Name', 'Grade Level', 'School Year Label']
        )
        self.df.columns = [col.replace(' ', '_') for col in self.df.columns]
        self.df = self.df[self.df['School_Year_Label'] == "2025 - 2026"]
        self.df = self.df.assign(Full_Name=self.df['First_Name'] + ' ' + self.df['Last_Name'])
        self.df = self.df[['Student_User_ID', 'Full_Name']]
        
        result = self.df.query("Full_Name == @self.name")['Student_User_ID']
        if result.empty:
            return "No ID Found for " + self.name
        return str(result.values[0])



class Parent:
    def __init__(self, name):
        self.name = name
    
    #Function to get a parent's child's user ID based on the parent entity and a specific graduation year
    def get_child_user_id(self,grad_year):
        self.grad_year = grad_year
        self.df = pd.read_csv(
            "/Users/jshwisberg/Desktop/Data/Basic List/Student Information/Students with Parents.csv",
            usecols=['Student User ID', 'Grad Year', 'Parent 1 Firstname', 'Parent 1 Lastname', 'Parent 2 Firstname', 'Parent 2 Lastname',
                    'Parent 3 First Name', 'Parent 3 Last Name','Parent 4 First Name', 'Parent 4 Last Name']
        )
        #Clean up column names & create new columns for full parent names
        self.df.columns = [col.replace(' ', '_') for col in self.df.columns]
        self.df = self.df.fillna("")
        self.df = self.df.assign(Parent1_Full_Name=self.df['Parent_1_Firstname'] + ' ' + self.df['Parent_1_Lastname'],
                                Parent2_Full_Name=self.df['Parent_2_Firstname'] + ' ' + self.df['Parent_2_Lastname'],
                                Parent3_Full_Name=self.df['Parent_3_First_Name'] + ' ' + self.df['Parent_3_Last_Name'],
                                Parent4_Full_Name=self.df['Parent_4_First_Name'] + ' ' + self.df['Parent_4_Last_Name'])
       
        #Melt the DataFrame to have one row per parent
        self.df = self.df.melt(
            id_vars=['Student_User_ID','Grad_Year'],
            value_vars=['Parent1_Full_Name', 'Parent2_Full_Name','Parent3_Full_Name', 'Parent4_Full_Name'],
            var_name='Parent_Type',
            value_name='Full_Name'
        )
        result = self.df.query("Full_Name == @self.name and Grad_Year ==@self.grad_year")['Student_User_ID']
        if result.empty:
            return "No Student ID found associated with " + self.name
        return str(result.values[0])