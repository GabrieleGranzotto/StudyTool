import os
import customtkinter as ctk
import numpy as np
import threading
import tempfile
import webbrowser
import base64
from question_training import QuestionExtraction

class IntegratedStudyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistema di Estrazione Domande")
        self.geometry("850x650")
        
        icon_path = os.path.join(os.path.dirname(__file__), 'icona.ico')
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
            
        self.btn_style = {
            "font": ("Arial", 16, "bold"),
            "fg_color": "#005ce6",      
            "hover_color": "#0043a8",   
            "corner_radius": 8,         
            "width": 160,
            "height": 45
        }
        
        self.engine = None
        self.subject_name = ""
        self.session_n = 0
        self.answered_count = 0
        self.session_qualities = []
        
        # --- CACHE E STORICO LLM ---
        self.llm_cache = {}          # Persiste fino alla chiusura dell'app: {question_text: {"text": str, "status": str}}
        self.session_questions = []  # Elenco delle domande estratte nella sessione corrente
        self.is_voice_recording = False
        
        self.questions_to_add = 0
        self.current_q_index = 1
        self.new_questions_list = []
        
        self.show_screen_1()

    def clear_screen(self):
        for widget in self.winfo_children():
            widget.destroy()

    def get_subjects(self):
        subjects = []
        for item in os.listdir('.'):
            if os.path.isdir(item) and not item.startswith(('.', '__')) and item != 'tests':
                if os.path.exists(os.path.join(item, 'questions.json')):
                    subjects.append(item)
        return sorted(subjects)

    # ==========================================
    # SCHERMATA 1: Selezione Materia
    # ==========================================
    def show_screen_1(self):
        self.clear_screen()
        self.bind('<Return>', lambda event: self.go_to_screen_router())
        
        ctk.CTkLabel(self, text="Buongiorno!", font=("Arial", 36, "bold")).pack(pady=(100, 15))
        ctk.CTkLabel(self, text="Questo è il software per l'estrazione intelligente delle domande.\nSeleziona la materia da studiare o aggiungine una.", font=("Arial", 18)).pack(pady=15)

        self.subjects = self.get_subjects()
        opzioni = self.subjects + ["+ Aggiungi nuova materia..."]
        
        self.combo_var = ctk.StringVar(value=opzioni[0] if self.subjects else opzioni[0])
        self.combo = ctk.CTkOptionMenu(self, variable=self.combo_var, values=opzioni, 
                                       command=self.on_combo_change, font=("Arial", 16), 
                                       width=250, height=40, corner_radius=8,
                                       fg_color="#005ce6", button_color="#0043a8", button_hover_color="#003380")
        self.combo.pack(pady=30)

        self.new_subject_entry = ctk.CTkEntry(self, placeholder_text="Nome nuova materia...", 
                                              width=300, height=45, font=("Arial", 16), corner_radius=8)
        if not self.subjects:
            self.new_subject_entry.pack(pady=10)

        btn_avanti = ctk.CTkButton(self, text="Avanti ➔", command=self.go_to_screen_router, **self.btn_style)
        btn_avanti.pack(side="bottom", anchor="se", padx=40, pady=40)

    def on_combo_change(self, choice):
        if choice == "+ Aggiungi nuova materia...":
            self.new_subject_entry.pack(pady=10)
            self.new_subject_entry.focus() 
        else:
            self.new_subject_entry.pack_forget()

    def go_to_screen_router(self):
        choice = self.combo_var.get()
        if choice == "+ Aggiungi nuova materia...":
            self.subject_name = self.new_subject_entry.get().strip().replace(" ", "_").lower()
            if not self.subject_name:
                return 
            self.show_screen_insert_count()
        else:
            self.subject_name = choice
            self.show_screen_2()

    # ==========================================
    # SCHERMATA INSERIMENTO
    # ==========================================
    def show_screen_insert_count(self):
        self.clear_screen()
        self.bind('<Return>', lambda event: self.start_insertion_loop())
        
        ctk.CTkLabel(self, text="Nuova Materia!", font=("Arial", 36, "bold"), text_color="#005ce6").pack(pady=(120, 25))
        ctk.CTkLabel(self, text="Quante domande vuoi inserire inizialmente?", font=("Arial", 20)).pack(pady=15)

        self.insert_n_entry = ctk.CTkEntry(self, placeholder_text="Es. 5", width=180, height=50, 
                                           font=("Arial", 22), justify="center", corner_radius=8)
        self.insert_n_entry.pack(pady=30)
        self.insert_n_entry.focus() 

        btn_avanti = ctk.CTkButton(self, text="Avanti ➔", command=self.start_insertion_loop, **self.btn_style)
        btn_avanti.pack(side="bottom", anchor="se", padx=40, pady=40)

    def start_insertion_loop(self):
        try:
            self.questions_to_add = int(self.insert_n_entry.get())
            if self.questions_to_add <= 0: return
        except ValueError:
            return
            
        self.new_questions_list = []
        self.current_q_index = 1
        self.show_screen_insert_question()

    def show_screen_insert_question(self):
        self.clear_screen()
        self.unbind('<Return>') 
        
        ctk.CTkLabel(self, text=f"Inserimento: Domanda {self.current_q_index} di {self.questions_to_add}", 
                     font=("Arial", 24, "bold"), text_color="#005ce6").pack(pady=(70, 20))
        
        self.q_textbox = ctk.CTkTextbox(self, width=650, height=200, font=("Arial", 18), 
                                        corner_radius=15, border_width=2, border_color="#333333")
        self.q_textbox.pack(pady=30)
        self.q_textbox.focus()
        
        btn_avanti = ctk.CTkButton(self, text="Avanti ➔", command=self.save_question_and_next, **self.btn_style)
        btn_avanti.pack(side="bottom", anchor="se", padx=40, pady=40)

    def save_question_and_next(self):
        testo = self.q_textbox.get("1.0", "end-1c").strip()
        if not testo:
            return 
            
        self.new_questions_list.append(testo)
        
        if self.current_q_index < self.questions_to_add:
            self.current_q_index += 1
            self.show_screen_insert_question()
        else:
            self.engine = QuestionExtraction(subject_name=self.subject_name, questions=[])
            self.engine.add_questions(self.new_questions_list)
            self.show_screen_2()

    # ==========================================
    # SCHERMATA 2: Setup Sessione
    # ==========================================
    def show_screen_2(self):
        self.clear_screen()
        self.bind('<Return>', lambda event: self.start_session())
        
        ctk.CTkLabel(self, text=f"Materia: {self.subject_name.replace('_', ' ').upper()}", 
                     font=("Arial", 32, "bold")).pack(pady=(110, 25))
        ctk.CTkLabel(self, text="A quante domande vuoi rispondere in questa sessione?", font=("Arial", 20)).pack(pady=15)

        self.n_entry = ctk.CTkEntry(self, placeholder_text="Es. 10", width=180, height=50, 
                                    font=("Arial", 22), justify="center", corner_radius=8)
        self.n_entry.pack(pady=30)
        self.n_entry.focus()

        btn_avanti = ctk.CTkButton(self, text="Inizia Sessione ➔", command=self.start_session, **self.btn_style)
        btn_avanti.pack(side="bottom", anchor="se", padx=40, pady=40)

    def start_session(self):
        try:
            self.session_n = int(self.n_entry.get())
            if self.session_n <= 0: return
        except ValueError:
            return

        if self.engine is None or self.engine.subject_name != self.subject_name:
            self.engine = QuestionExtraction(subject_name=self.subject_name, questions=[])

        self.answered_count = 0
        self.session_qualities = []
        self.session_questions = [] # Pulisce il tracciamento della sessione
        self.show_screen_3()

    # ==========================================
    # LOGICA DI PRE-FETCHING E CACHING LLM
    # ==========================================
    def _prefetch_llm(self, question_text):
        """Avvia la generazione in background non appena la domanda viene estratta."""
        if question_text in self.llm_cache:
            return # Risposta già in generazione o completata

        self.llm_cache[question_text] = {"text": None, "status": "fetching"}

        def worker():
            ans = self.engine.get_llm_answer(question_text)
            self.llm_cache[question_text]["text"] = ans
            self.llm_cache[question_text]["status"] = "done"

        threading.Thread(target=worker, daemon=True).start()

    def open_tutor_answer(self, question_text):
        """Gestisce il click sul pulsante Tutor con polling non bloccante e sicurezza UI."""
        cache = self.llm_cache.get(question_text)
        if not cache:
            self._prefetch_llm(question_text)
            cache = self.llm_cache[question_text]

        # Controllo di sicurezza: verifichiamo se il bottone della schermata 3 è ancora "vivo"
        btn_vivo = hasattr(self, 'btn_llm') and self.btn_llm.winfo_exists()

        if cache["status"] == "done":
            if btn_vivo:
                self.btn_llm.configure(state="normal", text="💡 Risposta Aperta (Riapri)", fg_color="#2b8a3e", hover_color="#2b7035")
            self._create_html_and_open_browser(cache["text"], question_text)
        else:
            if btn_vivo:
                self.btn_llm.configure(state="disabled", text="Generazione in corso...", fg_color="#555555")
            
            def wait_and_open():
                if cache["status"] == "done":
                    # Ri-controlliamo perché potrebbe essere stato distrutto durante l'attesa
                    if hasattr(self, 'btn_llm') and self.btn_llm.winfo_exists():
                        self.btn_llm.configure(state="normal", text="💡 Risposta Aperta (Riapri)", fg_color="#2b8a3e", hover_color="#2b7035")
                    self._create_html_and_open_browser(cache["text"], question_text)
                else:
                    self.after(200, wait_and_open)
                    
            wait_and_open()

    def _create_html_and_open_browser(self, markdown_text, question_text):
        b64_md = base64.b64encode(markdown_text.encode('utf-8')).decode('utf-8')
        
        html_template = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Risposta Tutor IA</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script>
        window.MathJax = {{
            tex: {{
                inlineMath: [['$','$'], ['\\\\(','\\\\)']],
                displayMath: [['$$','$$'], ['\\\\[','\\\\]']]
            }}
        }};
    </script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; color: #e0e0e0; line-height: 1.6; background-color: #121212; }}
        .question-box {{ background: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 30px; border-left: 6px solid #005ce6; font-size: 1.1em; color: #93c5fd; }}
        .answer-box {{ background: #1e1e1e; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); border: 1px solid #333; }}
        pre {{ background: #0d0d0d; color: #d4d4d4; padding: 15px; border-radius: 8px; overflow-x: auto; border: 1px solid #2a2a2a; }}
        code {{ font-family: 'Consolas', monospace; }}
        h1, h2, h3 {{ color: #3b82f6; }}
        a {{ color: #60a5fa; }}
    </style>
</head>
<body>
    <div class="question-box">
        <strong>Domanda Estratta:</strong><br><br>{question_text}
    </div>
    <div class="answer-box" id="content"></div>
    <script>
        const b64 = "{b64_md}";
        const rawMd = decodeURIComponent(escape(window.atob(b64)));
        document.getElementById('content').innerHTML = marked.parse(rawMd);
    </script>
</body>
</html>"""

        fd, path = tempfile.mkstemp(suffix=".html", text=True)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(html_template)
            
        webbrowser.open(f"file://{path}")

    # ==========================================
    # LOGICA DI VALUTAZIONE VOCALE MANUALE
    # ==========================================
    def toggle_voice_recording(self, question_text):
        """Gestisce il click del pulsante alternando tra Start e Stop."""
        if not self.is_voice_recording:
            # --- IL MICROFONO E' CHIUSO (REGISTRA) ---
            self.is_voice_recording = True
            self.btn_voice.configure(text="🛑 Ferma Registrazione e Valuta", fg_color="#c0392b", hover_color="#a53125")
            self.engine.start_recording()
        else:
            # --- IL MICROFONO E' CHIUSO (SPENTO) E PROCESSIAMO ---
            self.is_voice_recording = False
            self.btn_voice.configure(state="disabled", text="⚙️ Trascrizione e Valutazione...", fg_color="#f39c12")
            threading.Thread(target=self._process_voice_pipeline, args=(question_text,), daemon=True).start()

    def _process_voice_pipeline(self, question_text):
        try:
            transcript = self.engine.stop_and_transcribe()
            
            if not transcript or len(transcript.strip()) < 2:
                self.after(0, self._reset_voice_btn, "Silenzio rilevato. Riprova.")
                return

            # Manda a Gemma la trascrizione per il voto
            voto = self.engine.evaluate_student_answer(question_text, transcript)
            
            # Applica fisicamente il voto
            self.after(0, self._apply_voice_score, voto)
            
        except Exception as e:
            print(f"Errore Audio/S2T: {e}")
            self.after(0, self._reset_voice_btn, "Errore Microfono. Riprova.")

    def _apply_voice_score(self, voto):
        # Questo comando sposta materialmente il cursore sulla barra!
        self.qual_slider.set(voto)
        
        # Aggiorna il pulsante visivamente
        self.btn_voice.configure(state="normal", text=f"✅ Voto Assegnato: {voto}/5", fg_color="#27ae60", hover_color="#219653")
        
        # Dopo 4 secondi, ripristina il pulsante per permettere una nuova registrazione se desiderato
        self.after(4000, lambda: self.btn_voice.configure(text="🎤 Rispondi a Voce", fg_color="#8e44ad", hover_color="#732d91") if self.btn_voice.winfo_exists() else None)

    def _reset_voice_btn(self, error_msg):
        if hasattr(self, 'btn_voice') and self.btn_voice.winfo_exists():
            self.btn_voice.configure(state="normal", text=error_msg, fg_color="#c0392b", hover_color="#a53125")
            self.after(3000, lambda: self.btn_voice.configure(text="🎤 Rispondi a Voce", fg_color="#8e44ad", hover_color="#732d91") if self.btn_voice.winfo_exists() else None)

    # ==========================================
    # SCHERMATA 3: Loop Studio
    # ==========================================
    def show_screen_3(self):
        self.clear_screen()
        self.unbind('<Return>')
        
        self.engine.extract_question()
        idx = self.engine.last_extracted_question_idx
        domanda_testo = self.engine.questions[idx - 1]

        # Tracciamento domanda per la sessione corrente
        if domanda_testo not in self.session_questions:
            self.session_questions.append(domanda_testo)

        # 🚀 AVVIO IMMEDIATO PRE-FETCHING LLM IN BACKGROUND
        self._prefetch_llm(domanda_testo)

        valore_diff = self.engine.difficulties[idx - 1]
        valore_qual = self.engine.answer_qualities[idx - 1]
        if valore_qual == 0:
            valore_qual = 3

        ctk.CTkLabel(self, text=f"Domanda {self.answered_count + 1} di {self.session_n}", 
                     font=("Arial", 16, "bold"), text_color="gray").pack(pady=(30, 5))
                     
        ctk.CTkLabel(self, text=domanda_testo, font=("Arial", 26), 
                     wraplength=750, justify="center").pack(pady=20)

        # --- BOTTONE RISPOSTA VOCALE (Ora è sopra) ---
        self.btn_voice = ctk.CTkButton(self, text="🎤 Rispondi a Voce", 
                                       font=("Arial", 16, "bold"), fg_color="#8e44ad", hover_color="#732d91", 
                                       height=45, corner_radius=8,
                                       command=lambda: self.toggle_voice_recording(domanda_testo))
        self.btn_voice.pack(pady=(0, 15))  

        # --- BOTTONE TUTOR OLLAMA (Ora è sotto) ---
        # Stato iniziale del bottone in base alla cache
        is_ready = self.llm_cache.get(domanda_testo, {}).get("status") == "done"
        btn_text = "💡 Risposta Aperta (Riapri)" if is_ready else "💡 Consulta il Tutor (Browser)"
        btn_color = "#2b8a3e" if is_ready else "#ff8c00"
        hover_color = "#2b7035" if is_ready else "#cc7000"

        self.btn_llm = ctk.CTkButton(self, text=btn_text, font=("Arial", 16, "bold"), 
                                     fg_color=btn_color, hover_color=hover_color, 
                                     height=45, corner_radius=8,
                                     command=lambda: self.open_tutor_answer(domanda_testo))
        self.btn_llm.pack(pady=(0, 20)) 

        # Sliders
        slider_frame = ctk.CTkFrame(self, fg_color="transparent")
        slider_frame.pack(pady=10)

        ctk.CTkLabel(slider_frame, text="Difficoltà stimata (1-5):", font=("Arial", 16)).pack(pady=(10, 5))
        self.diff_slider = ctk.CTkSlider(slider_frame, from_=1, to=5, number_of_steps=4, width=250, height=20, button_color="#005ce6", button_hover_color="#0043a8")
        self.diff_slider.set(valore_diff) 
        self.diff_slider.pack(pady=5)

        ctk.CTkLabel(slider_frame, text="Qualità della tua risposta (1-5):", font=("Arial", 16)).pack(pady=(30, 5))
        self.qual_slider = ctk.CTkSlider(slider_frame, from_=1, to=5, number_of_steps=4, width=250, height=20, button_color="#005ce6", button_hover_color="#0043a8")
        self.qual_slider.set(valore_qual) 
        self.qual_slider.pack(pady=5)

        btn_avanti = ctk.CTkButton(self, text="Avanti ➔", command=self.submit_and_check, **self.btn_style)
        btn_avanti.pack(side="bottom", anchor="se", padx=40, pady=40)

    def submit_and_check(self):
        diff = int(self.diff_slider.get())
        qual = int(self.qual_slider.get())
        idx = self.engine.last_extracted_question_idx
        
        self.session_qualities.append(qual)
        self.engine._update_weights(idx, diff, qual)
        self.engine._export_question_weights()
        
        self.answered_count += 1
        
        if self.answered_count >= self.session_n:
            self.show_screen_4()
        else:
            self.show_screen_3()

    # ==========================================
    # SCHERMATA 4: Fine Sessione
    # ==========================================
    def show_screen_4(self):
        self.clear_screen()
        
        media = np.mean(self.session_qualities) if self.session_qualities else 0.0

        ctk.CTkLabel(self, text="Sessione Completata!", font=("Arial", 36, "bold"), text_color="#005ce6").pack(pady=(80, 20))
        ctk.CTkLabel(self, text=f"Hai finito di rispondere per oggi.\nHai risposto a {self.session_n} domande con una media di {media:.1f}/5.", font=("Arial", 20)).pack(pady=15)

        frame_bottoni = ctk.CTkFrame(self, fg_color="transparent")
        frame_bottoni.pack(pady=20)

        btn_grafici = ctk.CTkButton(frame_bottoni, text="Vedi Grafici", command=self.mostra_grafici_e_prosegui, **self.btn_style)
        btn_grafici.pack(side="left", padx=10)

        btn_review = ctk.CTkButton(frame_bottoni, text="📚 Rivedi Risposte Tutor", 
                                   font=("Arial", 16, "bold"), fg_color="#ff8c00", hover_color="#cc7000",
                                   height=45, corner_radius=8, command=self.show_screen_review_answers)
        btn_review.pack(side="left", padx=10)

        style_chiudi = self.btn_style.copy()
        style_chiudi.update({"fg_color": "#4d4d4d", "hover_color": "#333333"})
        btn_chiudi = ctk.CTkButton(frame_bottoni, text="Chiudi Subito", command=self.salta_grafici_e_prosegui, **style_chiudi)
        btn_chiudi.pack(side="left", padx=10)

    def mostra_grafici_e_prosegui(self):
        self.engine.intelligence() 
        self.engine.plot_progress()
        self.engine.plot_weights()
        self.show_screen_5()

    def salta_grafici_e_prosegui(self):
        self.engine.intelligence() 
        self.show_screen_5()

    # ==========================================
    # SCHERMATA REVISIONE RISPOSTE TUTOR
    # ==========================================
    def show_screen_review_answers(self):
        self.clear_screen()

        ctk.CTkLabel(self, text="Revisione Risposte della Sessione", font=("Arial", 28, "bold"), text_color="#005ce6").pack(pady=(40, 20))

        scroll_frame = ctk.CTkScrollableFrame(self, width=720, height=380, corner_radius=10)
        scroll_frame.pack(pady=10)

        for i, q_text in enumerate(self.session_questions, 1):
            item_frame = ctk.CTkFrame(scroll_frame, fg_color="#1a1a1a", corner_radius=8)
            item_frame.pack(fill="x", pady=8, padx=10)

            ctk.CTkLabel(item_frame, text=f"{i}. {q_text}", font=("Arial", 15), 
                         wraplength=480, justify="left").pack(side="left", padx=15, pady=12)

            btn_open = ctk.CTkButton(item_frame, text="📖 Apri Risposta", width=120, height=35,
                                     font=("Arial", 13, "bold"), fg_color="#2b8a3e", hover_color="#2b7035",
                                     command=lambda q=q_text: self.open_tutor_answer(q))
            btn_open.pack(side="right", padx=15, pady=12)

        btn_indietro = ctk.CTkButton(self, text="Indietro ➔", command=self.show_screen_4, **self.btn_style)
        btn_indietro.pack(side="bottom", anchor="se", padx=40, pady=30)

    # ==========================================
    # SCHERMATA 5: Sessione Aggiuntiva
    # ==========================================
    def show_screen_5(self):
        self.clear_screen()
        
        next_n = max(1, self.session_n // 2)

        ctk.CTkLabel(self, text="Un'ultima cosa...", font=("Arial", 36, "bold")).pack(pady=(120, 25))
        ctk.CTkLabel(self, text=f"Vuoi fare un'altra sessione di {next_n} domande?", font=("Arial", 20)).pack(pady=25)

        frame_bottoni = ctk.CTkFrame(self, fg_color="transparent")
        frame_bottoni.pack(pady=40)

        btn_si = ctk.CTkButton(frame_bottoni, text="Va bene", command=lambda: self.inizia_sessione_extra(next_n), **self.btn_style)
        btn_si.pack(side="left", padx=20)

        style_no = self.btn_style.copy()
        style_no.update({"fg_color": "#cc0000", "hover_color": "#990000"})
        btn_no = ctk.CTkButton(frame_bottoni, text="No, chiudi", command=self.destroy, **style_no)
        btn_no.pack(side="left", padx=20)

    def inizia_sessione_extra(self, n):
        self.session_n = n
        self.answered_count = 0
        self.session_qualities = []
        self.session_questions = []
        self.show_screen_3()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = IntegratedStudyApp()
    app.mainloop()