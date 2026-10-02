import unittest
import numpy as np
import json
import os
from unittest.mock import patch

# Sostituisci 'question_training' con il nome esatto del tuo file Python (senza l'estensione .py)
from question_training import QuestionExtraction

class TestQuestionExtraction(unittest.TestCase):
    
    def setUp(self):
        """Prepara l'ambiente prima di ogni singolo test."""
        self.test_questions = [
            "Domanda Facile 1", "Domanda Facile 2",
            "Domanda Media 1", "Domanda Media 2",
            "Domanda Difficile 1", "Domanda Difficile 2"
        ]
        self.qe = QuestionExtraction(self.test_questions, init_weights_policy="uniform")
        self.test_weights_file = "test_weights_export.json"
        
        # Sovrascriviamo temporaneamente l'output per evitare spam in console durante i test
        #self.patcher = patch('sys.stdout', new_callable=unittest.mock.MagicMock)
        #self.patcher.start()

    def tearDown(self):
        """Ripulisce i file creati durante i test per non sporcare la cartella."""
        #self.patcher.stop()
        if os.path.exists(self.test_weights_file):
            os.remove(self.test_weights_file)
        if os.path.exists('progress_log.json'):
            # Rimuoviamo il log di test se è stato creato
            os.remove('progress_log.json')

    def test_initialization(self):
        """Verifica che l'inizializzazione crei array delle dimensioni corrette."""
        self.assertEqual(len(self.qe.questions), 6)
        self.assertEqual(len(self.qe.difficulties), 6)
        self.assertEqual(len(self.qe.answer_qualities), 6)
        self.assertEqual(len(self.qe.answered_questions), 6)
        self.assertTrue(np.all(self.qe.difficulties == 5.0))
        self.assertTrue(np.all(self.qe.answer_qualities == 0.0))

    def test_probability_normalization(self):
        """Verifica che la somma dei pesi normalizzati sia SEMPRE 1 (evita il crash random.choice)."""
        # Forziamo dei valori estremi manuali
        self.qe.difficulties = np.array([1, 5, 2, 4, 3, 5])
        self.qe.answer_qualities = np.array([5, 1, 4, 2, 3, 5])
        self.qe.answered_questions = np.array([10, 0, 5, 2, 8, 1])
        
        # Ricalcoliamo i pesi
        self.qe.weights = self.qe._weight_policy(self.qe.difficulties, self.qe.answer_qualities)
        self.qe.norm_weight = self.qe._normalize_weights()
        
        # La somma deve essere 1.0 (usiamo isclose per via della precisione dei float)
        self.assertTrue(np.isclose(np.sum(self.qe.norm_weight), 1.0))
        # Nessuna probabilità deve essere negativa
        self.assertTrue(np.all(self.qe.norm_weight >= 0))

    def test_temperature_ratio_at_init(self):
        """Verifica che a 1 sola risposta il rapporto Best/Worst case sia circa 3.2."""
        # Creiamo un worst case (Diff=5, Qual=1) e un best case (Diff=1, Qual=5)
        difficulties = np.array([5, 1])
        answer_qualities = np.array([1, 5])
        
        # Mettiamo solo 1 risposta invece di 10, per mantenere la temperatura vicina a 25.0
        self.qe.answered_questions = np.array([0, 1]) 
        
        pesi_raw = self.qe._weight_policy(difficulties, answer_qualities)
        ratio = pesi_raw[0] / pesi_raw[1]
        
        # Verifichiamo che il rapporto (che a T=24.7 è circa 3.22) sia corretto
        self.assertAlmostEqual(ratio, 3.2, places=1, msg=f"Rapporto iniziale inatteso: {ratio}")

    def test_temperature_ratio_at_100_answers(self):
        """Verifica che dopo 100 domande il rapporto Best/Worst case diventi circa 23:1."""
        difficulties = np.array([5, 1])
        answer_qualities = np.array([1, 5])
        # Simuliamo 100 domande totali
        self.qe.answered_questions = np.array([0, 100])
        
        pesi_raw = self.qe._weight_policy(difficulties, answer_qualities)
        ratio = pesi_raw[0] / pesi_raw[1]
        
        # Verifichiamo che a regime il rapporto sia attorno a 23
        self.assertAlmostEqual(ratio, 23.0, places=0, msg=f"Rapporto a 100 iterazioni inatteso: {ratio}")

    @patch('builtins.input', side_effect=['3', '4']) 
    def test_extraction_and_evaluation_cycle(self, mock_input):
        """Verifica che un ciclo completo di estrazione e valutazione aggiorni correttamente gli stati."""
        initial_answered_sum = np.sum(self.qe.answered_questions)
        
        self.qe.extract_question()
        idx = self.qe.last_extracted_question_idx
        self.qe.evaluate_question() # Userà i valori '3' e '4' forniti dal mock_input
        
        # Verifichiamo che il contatore delle risposte sia salito di 1
        self.assertEqual(np.sum(self.qe.answered_questions), initial_answered_sum + 1)
        # Verifichiamo che i valori inseriti siano stati salvati
        self.assertEqual(self.qe.difficulties[idx - 1], 3)
        self.assertEqual(self.qe.answer_qualities[idx - 1], 4)

    def test_export_and_import_persistence(self):
        """Verifica che i salvataggi JSON vengano scritti e ricaricati in modo identico."""
        # Modifichiamo lo stato manualmente
        self.qe.difficulties[0] = 2
        self.qe.answer_qualities[0] = 5
        self.qe.answered_questions[0] = 12
        
        # Esportiamo
        self.qe.export_question_weights(self.test_weights_file)
        self.assertTrue(os.path.exists(self.test_weights_file))
        
        # Reimportiamo in una nuova istanza
        nuovo_qe = QuestionExtraction(question_weights_file=self.test_weights_file)
        
        # Verifichiamo che i dati siano identici
        self.assertEqual(nuovo_qe.difficulties[0], 2)
        self.assertEqual(nuovo_qe.answer_qualities[0], 5)
        self.assertEqual(nuovo_qe.answered_questions[0], 12)
        self.assertEqual(len(nuovo_qe.questions), 6)

    @patch('builtins.input', return_value='3')
    def test_stress_simulation(self, mock_input):
        """Simula 150 estrazioni rapide per assicurarsi che non ci siano crash (es. divisioni per zero)."""
        try:
            for _ in range(150):
                self.qe.extract_question()
                self.qe.evaluate_question()
        except Exception as e:
            self.fail(f"Il ciclo di stress test ha generato un'eccezione inaspettata: {e}")
            
        # Assicuriamoci che a fine stress test la somma delle prob. sia ancora 1
        self.assertTrue(np.isclose(np.sum(self.qe.norm_weight), 1.0))

if __name__ == '__question_training__':
    # Esegue tutti i test e stampa il report in console
    unittest.question_training(verbosity=2)