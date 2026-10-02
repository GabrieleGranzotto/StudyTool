import unittest
import os
import shutil
from question_training import QuestionExtraction

class TestDirectoryArchitecture(unittest.TestCase):
    def test_folder_and_json_creation(self):
        materia_test = "test_architettura_temporanea"
        # Inizializza il motore
        qe = QuestionExtraction(subject_name=materia_test, questions=["Test 1", "Test 2"])
        qe._export_question_weights() # Forza il salvataggio
        
        # Verifica che la cartella e il JSON esistano nel percorso corretto
        self.assertTrue(os.path.exists(materia_test))
        self.assertTrue(os.path.exists(os.path.join(materia_test, "questions.json")))
        
        # Pulizia post-test
        shutil.rmtree(materia_test)

if __name__ == '__main__':
    unittest.main()