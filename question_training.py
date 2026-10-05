import requests, re, json, os, pyaudio, wave, whisper, tempfile, threading
from datetime import date

import numpy as np
import matplotlib.pyplot as plt

class QuestionExtraction:
    def __init__(self, subject_name, questions=None, init_weights_policy="uniform"):
        # Impostazione della cartella del progetto
        self.subject_name = subject_name
        self.master_dir = os.path.join(os.getcwd(), 'subjects')
        self.base_dir = os.path.join(self.master_dir, subject_name)
        
        # Crea la cartella in modo sicuro se non esiste già
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Percorsi standardizzati
        self.question_weights_file = os.path.join(self.base_dir, 'questions.json')
        self.log_file = os.path.join(self.base_dir, 'progress_log.json')
        
        # Logica di importazione unificata
        if os.path.exists(self.question_weights_file):
            with open(self.question_weights_file, 'r') as f:
                data = json.load(f)
                self.questions = data['questions']
                self.difficulties = np.array(data['difficulties'])
                self.answer_qualities = np.array(data['answer_qualities'])
                self.answered_questions = np.array(data['answered_questions'])
                self._init_weights(policy="import", imported_weights=(self.difficulties, self.answer_qualities))
        elif questions is not None:
            self.questions = questions
            self.answered_questions = np.zeros(len(questions))
            self._init_weights(init_weights_policy)
        else:
            raise ValueError(f"Nessun file questions.json trovato in '{self.base_dir}' e nessuna lista di domande fornita all'avvio.")
        
        self.population = np.arange(1, len(self.questions) + 1)
        self.weighted_probability_mask = np.ones(len(self.questions), dtype=float)
        self.recent_buffer = []
        self.introduction()

        self.is_recording = False
        self.whisper_model = None
        plt.style.use('ggplot')

    def introduction(self):
        print(f"Welcome to the Question Extraction System for: {self.subject_name.upper()}")
        print("You will be presented with questions, and you can evaluate them based on difficulty and your answer quality.")
        print("Let's get started!\n")

    def _weight_policy(self, difficulties, answer_qualities):
        # Protezione anti-crash se inizializziamo il motore prima di aver inserito le domande
        if len(difficulties) == 0:
            return np.array([])
            
        base_logits = difficulties * (6.0 - answer_qualities)
        
        # Aggiunta sicurezza sulla lunghezza dell'array
        if len(self.answered_questions) > 0 and np.max(self.answered_questions) > 0:
            max_answers = np.max(self.answered_questions)
            starvation_ratio = (max_answers - self.answered_questions) / max_answers
            
            beta = 0.2 
            boost_factor = 1.0 + (beta * starvation_ratio)
            boosted_logits = base_logits * boost_factor
        else:
            boosted_logits = base_logits
            
        total_answers = np.sum(self.answered_questions)
        t_init = 25.0      
        t_min = 5.0       
        decay_rate = 0.01 
        
        current_temp = max(t_min, t_init * np.exp(-decay_rate * total_answers))
        
        stabilized_logits = boosted_logits - np.max(boosted_logits)
        
        return np.exp(stabilized_logits / current_temp)

    def _init_weights(self, policy, imported_weights=None):
        n_questions = len(self.questions)

        self.difficulties = np.ones(n_questions)*5
        self.answer_qualities = np.ones(n_questions)*0
        if policy == "uniform":
            pass
        elif policy == "random":
            self.difficulties = np.random.randint(1, 6, size=n_questions)
            self.answer_qualities = np.random.randint(1, 6, size=n_questions)
        elif policy == "import":
            self.difficulties = imported_weights[0]
            self.answer_qualities = imported_weights[1]
        else:
            raise ValueError("Invalid initialization policy. Choose 'uniform' or 'random'.")
        self.weights = self._weight_policy(self.difficulties, self.answer_qualities)
        self.norm_weight = self._normalize_weights(self.weights)

    def _normalize_weights(self, weights):
        if len(weights) == 0 or np.sum(weights) == 0:
            return weights
        return weights / np.sum(weights)

    def _update_weights(self, idx, difficulty, answer_quality):
        self.difficulties[idx - 1] = difficulty
        self.answer_qualities[idx - 1] = answer_quality
        self.weights = self._weight_policy(self.difficulties, self.answer_qualities)
        self.norm_weight = self._normalize_weights(self.weights)

    def add_questions(self, new_questions_list):
        if not new_questions_list:
            return
            
        n_new = len(new_questions_list)
        self.questions.extend(new_questions_list)
        
        # Aggiungiamo i pesi di default (Diff=5, Qualità=0, Risposte=0) 
        # come se fosse un _init_weights per le sole nuove arrivate
        self.difficulties = np.append(self.difficulties, np.ones(n_new) * 5.0)
        self.answer_qualities = np.append(self.answer_qualities, np.zeros(n_new))
        self.answered_questions = np.append(self.answered_questions, np.zeros(n_new))
        self.weighted_probability_mask = np.append(self.weighted_probability_mask, np.ones(n_new, dtype=float))
        
        self.population = np.arange(1, len(self.questions) + 1)
        
        # Ricalcoliamo le distribuzioni globali
        self.weights = self._weight_policy(self.difficulties, self.answer_qualities)
        self.norm_weight = self._normalize_weights(self.weights)
        
        # Salvataggio immediato sul file JSON della materia
        self._export_question_weights()

    def extract_question(self):
        weighted_sample_idx, question = self._extract_question()
        print(f"Extracted Question {weighted_sample_idx}: {question}")

    def _extract_question(self):
        LOW_PROB_VALUE = 0.05
        LOW_PROB_NUM_QUESTIONS = 5
        final_norm_weight = self._normalize_weights(self.norm_weight * self.weighted_probability_mask)
        weighted_sample_idx = np.random.choice(self.population, p=final_norm_weight)
        self.answered_questions[weighted_sample_idx - 1] += 1
        self.last_extracted_question_idx = weighted_sample_idx
        self.weighted_probability_mask[weighted_sample_idx - 1] = LOW_PROB_VALUE
        self.recent_buffer.append(weighted_sample_idx)
        if len(self.recent_buffer) > LOW_PROB_NUM_QUESTIONS:
            oldest_idx = self.recent_buffer.pop(0)
            self.weighted_probability_mask[oldest_idx - 1] = 1.0
        return weighted_sample_idx, self.questions[weighted_sample_idx - 1]

    def evaluate_question(self):
        idx = self.last_extracted_question_idx
        print(f"Evaluating question {idx}:")
        
        while True:
            try:
                difficulty = int(input("Enter difficulty level [1-5]: "))
                if 1 <= difficulty <= 5:
                    break
                print("Please, insert a valid number between 1 and 5.")
            except ValueError:
                print("Invalid input. You must insert an integer.")
                
        while True:
            try:
                answer_quality = int(input("How good did you answer the question? [1-5]: "))
                if 1 <= answer_quality <= 5:
                    break
                print("Please, insert a valid number between 1 and 5.")
            except ValueError:
                print("Invalid input. You must insert an integer.")
        self._update_weights(idx, difficulty, answer_quality)

    def export_question_weights(self):
        user_input = input("Do you want to export the question weights to a JSON file? [y/n]: ")
        if user_input.lower() == 'y':
            print(f"Exporting question weights to {self.question_weights_file}...")
            self._export_question_weights()

    def _export_question_weights(self):
        data = {
            "questions": self.questions,
            "difficulties": self.difficulties.tolist(),
            "answer_qualities": self.answer_qualities.tolist(),
            "answered_questions": self.answered_questions.tolist()
        }
        with open(self.question_weights_file, 'w') as f:
            json.dump(data, f)

    def intelligence(self):
        print("Intelligence function give to the user informations about the questions and his preparation.")
        print("Here are some insights about the questions and your performance:")
        hardest_questions_idx, worst_answered_questions_idx = self._intelligence()

        print("Hardest Questions:")
        for idx in hardest_questions_idx:
            print(f"  {idx + 1}. {self.questions[idx]}")

        print("Worst Answered Questions:")
        for idx in worst_answered_questions_idx:
            print(f"  {idx + 1}. {self.questions[idx]}")

        print(f"Expected Mark: {self.expected_mark:.2f}")
        print(f"Number of Answered Questions: {self.number_of_answered_questions}")
        print(f"Question with the least answers: {self.questions[self.argmin_number_of_answered_questions]} (Answered {self.number_of_least_answered_question} times)")

    def _intelligence(self):
        hardest_questions_idx = np.argsort(self.difficulties)[-3:][::-1]
        worst_answered_questions_idx = np.argsort(self.answer_qualities)[:3]
        self.expected_mark = np.mean(self.answer_qualities)*(30/5)
        self.number_of_answered_questions = np.sum(self.answered_questions)
        self.argmin_number_of_answered_questions = np.argmin(self.answered_questions)
        self.number_of_least_answered_question = self.answered_questions[self.argmin_number_of_answered_questions]

        log_progress = {
            "date": str(date.today()),
            "number_of_answered_questions": self.number_of_answered_questions,
            "number_of_least_answered_question": self.number_of_least_answered_question,
            "expected_mark": self.expected_mark
        }

        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_progress) + "\n")

        return hardest_questions_idx, worst_answered_questions_idx

    def plot_progress(self):
        daily_logs = {}
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    if line.strip(): 
                        entry = json.loads(line)
                        # Usando la data come chiave, sovrascriviamo le sessioni precedenti
                        # mantenendo solo lo stato finale della giornata
                        daily_logs[entry['date']] = entry
        except FileNotFoundError:
            print("No log found. Answer some questions to generate the file!")
            return

        if not daily_logs:
            print("The log file is empty.")
            return

        # Estraiamo i dati raggruppati, ordinandoli cronologicamente
        dates = sorted(daily_logs.keys())
        number_of_answered_questions = [daily_logs[d]['number_of_answered_questions'] for d in dates]
        expected_marks = [daily_logs[d]['expected_mark'] for d in dates]

        plt.figure(figsize=(12, 6))
        
        plt.subplot(1, 2, 1)
        plt.plot(dates, number_of_answered_questions, marker='o')
        plt.xticks(rotation=45)
        plt.xlabel('Date')
        plt.ylabel('Number of Answered Questions')
        plt.title('Progress Over Time')

        plt.subplot(1, 2, 2)
        plt.plot(dates, expected_marks, marker='o', color='orange')
        plt.xticks(rotation=45)
        plt.xlabel('Date')
        plt.ylabel('Expected Mark')
        plt.title('Expected Mark Over Time')

        plt.tight_layout()
        plt.savefig(os.path.join(self.base_dir, 'progress_over_time.png'))
        plt.show()

    def plot_weights(self):
        plt.bar(self.population, self.norm_weight)
        plt.xlabel('Question Index')
        plt.ylabel('Normalized Weight')
        plt.title('Normalized Weights of Questions')
        plt.savefig(os.path.join(self.base_dir, 'normalized_weights_question.png'))
        plt.show()

        plt.bar(self.population, self.difficulties, color='orange')
        plt.xlabel('Question Index')
        plt.ylabel('Difficulties')
        plt.title('Difficulties of Questions')
        plt.savefig(os.path.join(self.base_dir, 'difficulties_question.png'))
        plt.show()

        plt.bar(self.population, self.answer_qualities, color='green')
        plt.xlabel('Question Index')
        plt.ylabel('Answer Qualities')
        plt.title('Answer Qualities of Questions')
        plt.savefig(os.path.join(self.base_dir, 'answer_qualities_question.png'))
        plt.show()

    def get_llm_answer(self, question_text):
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "gemma4:e4b", 
            "prompt": f"Sei un tutor universitario esperto in informatica e intelligenza artificiale che deve rispondere a domande di {self.subject_name}. Rispondi a questa domanda in modo tecnico ma conciso:\n\n{question_text}",
            "stream": False
        }
        try:
            # Impostiamo un timeout lungo (120s) per dare tempo all'LLM locale di caricarsi
            response = requests.post(url, json=payload, timeout=120)
            if response.status_code == 200:
                return response.json().get("response", "Nessuna risposta generata.")
            else:
                return f"Errore API: {response.status_code}"
        except Exception as e:
            return f"[Errore di Connessione] Impossibile raggiungere Ollama. Il servizio è chiuso?\n\nDettagli tecnici: {e}"

    def start_recording(self):
        """Apre lo stream audio e inizia a registrare finché non viene chiuso."""
        self.is_recording = True
        self.audio_frames = []
        self.p = pyaudio.PyAudio()
        
        # exception_on_overflow=False è vitale per evitare crash del microfono su Windows
        self.stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=16000, 
                                  input=True, frames_per_buffer=1024)

        def record_loop():
            # Limite massimo di sicurezza: 10 minuti (600 secondi)
            max_frames = int(16000 / 1024 * 600)
            for _ in range(max_frames):
                if not self.is_recording:
                    break
                try:
                    data = self.stream.read(1024, exception_on_overflow=False)
                    self.audio_frames.append(data)
                except Exception:
                    pass
                    
            # Chiusura sicura delle porte hardware
            try:
                self.stream.stop_stream()
                self.stream.close()
                self.p.terminate()
            except Exception:
                pass

        # Il loop di registrazione gira in background
        threading.Thread(target=record_loop, daemon=True).start()

    def stop_and_transcribe(self):
        """Ferma l'audio, bypassa FFmpeg e trascrive direttamente dalla RAM."""
        # Il microfono viene chiuso
        self.is_recording = False
        
        # Se non ha registrato nulla, evitiamo crash
        if not self.audio_frames:
            return ""

        # 1. Carica il modello (richiede qualche secondo in più solo la primissima volta)
        if self.whisper_model is None:
            print("Caricamento modello Whisper in memoria...")
            self.whisper_model = whisper.load_model("base")

        # 2. Convertiamo i byte in un formato matematico float32 compreso tra -1 e 1 per Whisper
        audio_data = b''.join(self.audio_frames)
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

        print("Trascrizione in corso tramite array in RAM...")
        
        # 3. Trascrizione immediata (nessun file salvato sul disco!)
        result = self.whisper_model.transcribe(audio_np, language="it", fp16=False)
        
        return result["text"]

    def evaluate_student_answer(self, question_text, student_answer):
        """Invia la trascrizione all'LLM e forza l'output a un numero da 1 a 5."""
        url = "http://localhost:11434/api/generate"
        
        prompt = (
            f"Sei un esaminatore universitario che valuta le risposte degli studenti ad un esame."
            f"Tieni in conto che la risposta dello studente è solo orale e potrebbe non avere formule e simboli matematici corretti e ripetizioni possibili."
            f"La domanda era: '{question_text}'. "
            f"La risposta dello studente è stata: '{student_answer}'. "
            f"Valuta la qualità e la correttezza della risposta dello studente con un numero intero da 1 (Pessima) a 5 (Eccellente)."
            f"Criteri di valutazione: Completezza, Accuratezza, Chiarezza e Pertinenza."
            f"RISPONDI ESCLUSIVAMENTE CON IL NUMERO, SENZA ALCUNA PAROLA O SPIEGAZIONE AGGIUNTIVA."
        )
        
        payload = {
            "model": "gemma:e4b",
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                ans = response.json().get("response", "3")
                match = re.search(r'[1-5]', ans)
                if match:
                    return int(match.group())
                return 3 
            else:
                return 3
        except Exception:
            return 3

####################################################################################
####################################################################################

if __name__ == "__main__":
    # Esempio: Inizializziamo passando solo il nome della materia e la prima lista di domande
    materia = "fisica_quantistica"
    domande_iniziali = ["Che cos'è un fotone?", "Spiega l'equazione di Schrödinger", "Cos'è l'entanglement?"]

    # Al primo avvio creerà la cartella 'fisica_quantistica' e utilizzerà 'domande_iniziali'.
    # Ai successivi avvii, caricherà in automatico da 'fisica_quantistica/questions.json'
    qe = QuestionExtraction(subject_name=materia, questions=domande_iniziali, init_weights_policy="uniform")

    for _ in range(3):
        qe.extract_question()
        qe.evaluate_question()

    qe.intelligence()
    qe.plot_progress()
    qe.plot_weights()
    qe.export_question_weights()