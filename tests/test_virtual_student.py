import unittest
import os
import json
from unittest.mock import patch
from question_training import QuestionExtraction

class TestVirtualStudentBehavior(unittest.TestCase):
    
    def setUp(self):
        # Usiamo 3 archetipi di domanda per testare lo scheduling
        self.test_questions = [
            "Domanda 1: Facile e nota", 
            "Domanda 2: Media", 
            "Domanda 3: Difficile e ignota"
        ]
        self.qe = QuestionExtraction(self.test_questions, init_weights_policy="uniform")
        self.log_file = 'progress_log.json'
        
        # Pulizia iniziale per non inquinare il test con vecchi log
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
            
        # Silenziamo l'output su console per avere un report pulito
        self.patcher = patch('sys.stdout', new_callable=unittest.mock.MagicMock)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
        if os.path.exists('progress_over_time.png'):
            os.remove('progress_over_time.png')

    def mock_virtual_student_input(self, prompt):
        """
        L'agente simulato guarda quale domanda è stata estratta 
        e risponde sempre in modo coerente al suo archetipo.
        """
        idx = self.qe.last_extracted_question_idx
        if "difficulty" in prompt.lower():
            # Restituisce 1 per la Q1, 3 per la Q2, 5 per la Q3
            return str({1: 1, 2: 3, 3: 5}[idx])
        else:
            # Restituisce 5 (ottima) per Q1, 3 per Q2, 1 (pessima) per Q3
            return str({1: 5, 2: 3, 3: 1}[idx])

    # Blocchiamo l'apertura fisica della finestra dei grafici durante i test
    @patch('matplotlib.pyplot.show')
    @patch('matplotlib.pyplot.savefig')
    def test_500_iterations_learning_trajectory(self, mock_savefig, mock_show):
        """Simula 500 cicli completi di studio e ne verifica i risultati."""
        
        # Sostituiamo l'input da tastiera con il nostro studente virtuale
        with patch('builtins.input', side_effect=self.mock_virtual_student_input):
            for i in range(1, 501):
                self.qe.extract_question()
                self.qe.evaluate_question()
                
                # Ogni 100 estrazioni, simuliamo che l'utente chieda i log
                if i % 100 == 0:
                    self.qe.intelligence()
        
        # --- VERIFICA 1: LO SCHEDULING (LA TRAIETTORIA) ---
        ans = self.qe.answered_questions
        q_facile = ans[0]
        q_media = ans[1]
        q_difficile = ans[2]
        
        # L'algoritmo deve aver "martellato" sulla domanda difficile,
        # un po' sulla media, e quasi ignorato quella facile.
        self.assertGreater(q_difficile, q_media, "La domanda difficile non è stata estratta più della media!")
        self.assertGreater(q_media, q_facile, "La domanda media non è stata estratta più della facile!")
        
        # Vogliamo che la scrematura sia evidente: la difficile deve uscire NETTAMENTE di più della facile
        self.assertTrue(q_difficile > q_facile * 5, 
                        msg=f"Scrematura debole! Facile: {q_facile} volte, Difficile: {q_difficile} volte.")

        # --- VERIFICA 2: I LOG JSON ---
        self.assertTrue(os.path.exists(self.log_file), "Il file di log non è stato creato!")
        
        with open(self.log_file, 'r') as f:
            lines = f.readlines()
            
        self.assertEqual(len(lines), 5, "Ci aspettiamo 5 salvataggi (uno ogni 100 domande).")
        
        # Verifichiamo il contenuto dei JSON
        for line in lines:
            # JSONDecodeError scatterà qui in automatico se c'è un errore di sintassi (es. mancano le virgole)
            entry = json.loads(line) 
            
            # Verifichiamo che ci siano tutti i parametri chiave
            self.assertIn("date", entry)
            self.assertIn("number_of_answered_questions", entry)
            self.assertIn("expected_mark", entry)
            
            # Matematica di controllo: se l'agente risponde sempre 5, 3, 1... 
            # la media delle Qualità attuali è 3.0. 
            # Il tuo calcolo è 3.0 * (30/5) = 18.0.
            self.assertAlmostEqual(entry["expected_mark"], 18.0, 
                                   msg="Il calcolo del voto atteso (expected_mark) è errato.")
            
        # --- VERIFICA 3: IL PLOTTING ---
        try:
            self.qe.plot_progress()
        except Exception as e:
            self.fail(f"plot_progress() è andato in crash leggendo il log: {e}")
            
        # Verifica che matplotlib abbia tentato di salvare il PNG
        mock_savefig.assert_called_with('progress_over_time.png')

if __name__ == '__main__':
    unittest.main(verbosity=2)