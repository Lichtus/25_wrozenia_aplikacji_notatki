"""
Konfiguracja Telegram Voice Notes Bot
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_IDS = [int(uid) for uid in os.getenv("ALLOWED_USER_IDS", "").split(",") if uid]

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Dostawca transkrypcji: "assemblyai" albo "openai".
#
# AssemblyAI grupuje mówców globalnie po całym nagraniu, więc etykiety są
# spójne od początku do końca. OpenAI grupuje w obrębie fragmentu i na dłuższych
# nagraniach potrafi zarówno rozjechać etykiety, jak i skleić dwie osoby w jedną.
# Cena AssemblyAI to ok. połowa stawki OpenAI. Polska transkrypcja bywa u niego
# odrobinę mniej dokładna — stąd przełącznik, a nie zamiana na sztywno.
TRANSCRIPTION_PROVIDER = os.getenv("TRANSCRIPTION_PROVIDER", "assemblyai")

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
ASSEMBLYAI_LANGUAGE = os.getenv("ASSEMBLYAI_LANGUAGE", "pl")

# Modele OpenAI — używane, gdy dostawcą jest "openai" albo awaryjnie.
TRANSCRIPTION_MODEL = "gpt-4o-transcribe-diarize"
WHISPER_MODEL = "whisper-1"
GPT_MODEL = "gpt-4o-mini"

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "voice_notes.db")
DATABASE_URL = os.getenv("DATABASE_URL")  # PostgreSQL/Supabase URL (opcjonalne)

# Prompts
EXTRACTION_PROMPT = """Jesteś precyzyjnym asystentem AI ds. analizy audio i notatek głosowych.

Twoim zadaniem jest przetworzenie poniższej transkrypcji (może to być dialog wieloosobowy, spotkanie biznesowe lub swobodny monolog/strumień myśli) na ustrukturyzowaną, konkretną notatkę.

ZASADY:
1. Pomiń wtrącenia, powtórzenia, zacięcia językowe i nieistotny small talk.
2. Zachowaj esencję, fakty, liczby, pomysły i kontekst wypowiedzi.
3. Dopasuj formę sekcji do typu nagrania — patrz WYBÓR TRYBU niżej.
4. Nie wymyślaj informacji, których nie ma w tekście.
5. Pisz z perspektywy autora notatki — nie "użytkownik powiedział", tylko wprost o rzeczy.

WYBÓR TRYBU — ZRÓB TO NAJPIERW:
Sprawdź, czy transkrypcja ma oznaczonych rozmówców (np. "Rozmówca 1:").

A) ROZMOWA WIELOOSOBOWA → treść niosą "bloki" i "rozmowcy".
   Pole "kluczowe_mysli" MUSI być puste: []. Bez wyjątków.
   Powód: "bloki" tną materiał wg wątku, "rozmowcy" wg osoby. Trzecie
   cięcie wg tematu opisywałoby po raz trzeci to samo.

B) MONOLOG (jeden mówca albo brak oznaczeń) → treść niesie "opis"
   i "kluczowe_mysli". Pola "bloki" i "rozmowcy" MUSZĄ być puste: [].
   "kluczowe_mysli" to w tym trybie GŁÓWNY nośnik treści, nie dodatek.
   Jeśli w nagraniu jest jakiekolwiek rozumowanie — powody, liczby,
   porównania, doświadczenia z przeszłości, argumenty za i przeciw —
   MUSI się tam znaleźć. "opis" to tylko 2-3 zdania streszczenia i z
   natury gubi te szczegóły, więc nie jest powtórzeniem.
   Puste [] zostaw wyłącznie wtedy, gdy nagranie to jedna-dwie sprawy
   podane bez żadnego uzasadnienia.

Nigdy nie wypełniaj obu zestawów naraz.

TRANSKRYPCJA:
"{transcription}"

Odpowiedz TYLKO w formacie JSON:
{{
  "temat": "krótki tytuł notatki (max 80 znaków)",
  "kategoria": "Praca/Dom/Inne",
  "confidence": 0.85,
  "opis": "PODSUMOWANIE: 2-3 zwięzłe zdania opisujące główny wątek, cel lub esencję nagrania",
  "rozmowcy": [
    {{"mowca": "Rozmówca 1", "podsumowanie": "co ta osoba wniosła do rozmowy, jej stanowisko i najważniejsze wypowiedzi, 1-2 zdania. NIE zaczynaj od etykiety — interfejs drukuje ją sam. Źle: 'Rozmówca 1 podkreślił...'. Dobrze: 'Podkreślił...'"}}
  ],
  "bloki": [
    {{"kategoria": "postepy",
      "tytul": "nazwa omawianego wątku",
      "czas": "MM:SS — znacznik z transkrypcji, kiedy wątek się zaczyna",
      "punkty": ["Rozmówca 1 zauważył, że ... (kto co powiedział, z konkretami)"]}}
  ],
  "kluczowe_mysli": [
    {{"watek": "nazwa poruszonego tematu", "tresc": "najważniejsze spostrzeżenia, omówione fakty lub pomysły w tym wątku"}}
  ],
  "zadania": [
    {{"osoba": "etykieta rozmówcy odpowiedzialnego, np. Rozmówca 2, albo null gdy nie przypisano",
      "tresc": "konkretne działanie, zrozumiałe samodzielnie",
      "czas": "MM:SS gdy da się ustalić, inaczej null"}}
  ],
  "terminy": ["daty, godziny i ustalenia czasowe, które nie są zadaniami"],
  "decyzje": ["decyzje, konkluzje lub definitywne przemyślenia autora"],
  "otwarte_watki": ["pytanie lub wątpliwość, która PADŁA w nagraniu i została bez odpowiedzi — nie twoje pytania do tematu"]
}}

OBJAŚNIENIA SEKCJI:
- opis = Podsumowanie (Overview), esencja w 2-3 zdaniach
- rozmowcy = kto co mówił; tylko tryb A. W trybie B pusta tablica []
- bloki = wątki spotkania, każdy z kategorią, znacznikiem czasu i punktami
  przypisanymi do osób. Kategorie:
    "postepy"  - co przeanalizowano, ustalono, jak idzie praca
    "wyzwania" - problemy, luki, ryzyka, zmiany kierunku
    "kroki"    - co dalej, plany, nadchodzące etapy
  Tylko tryb A. W trybie B pusta tablica [].
- zadania = obiekty z osobą odpowiedzialną, treścią i znacznikiem czasu
- kluczowe_mysli = Główne myśli i tematy, pogrupowane w bloki tematyczne —
  powody, liczby, argumenty za i przeciw, porównania, doświadczenia z
  przeszłości. W trybie B to główny nośnik treści. W trybie A: []
- zadania = Zadania i kolejne kroki, każde jako konkretne działanie
- decyzje = rzeczy ROZSTRZYGNIĘTE. NIE wpisuj tu ustaleń, które są już
  zadaniem albo blokiem o kategorii "kroki". Jeśli "PM zwołuje kick-off"
  jest zadaniem, to nie jest osobną decyzją.
  Wahanie się NIE jest decyzją: "rozważam X", "zastanawiam się, czy X",
  "chyba zrobimy X" to kluczowe_mysli (tryb B) albo blok "wyzwania"
  (tryb A). Do decyzji trafia tylko to, co zapadło
- otwarte_watki = pytania i wątpliwości, które PADŁY W NAGRANIU jako
  nierozstrzygnięte. Nie formułuj własnych pytań do tematu ani sugestii,
  co warto byłoby jeszcze przemyśleć — to jest wymyślanie treści

DOPRECYZOWANIE TREŚCI:
- Każde zadanie musi być zrozumiałe SAMODZIELNIE, bez czytania reszty notatki.
  Zapisz: co zrobić, czego lub kogo dotyczy, po co albo w jakim kontekście,
  oraz termin jeśli padł. Jedno zdanie, ale pełne.
  Źle: "Wysłać specyfikację"
  Dobrze: "Wysłać Kowalskiemu specyfikację techniczną środowiska pilotażowego
  do piątku, bo w poniedziałek ma komitet sterujący"
- kluczowe_mysli NIE MOGĄ powtarzać zadań ani decyzji. Ich rolą jest kontekst,
  przyczyny, liczby, argumenty i konsekwencje. Zapisz DLACZEGO coś zostało
  powiedziane i co z tego wynika, 2-3 zdania na wątek.
- Zachowaj wszystkie konkrety, które padły: kwoty, procenty, terminy, nazwy,
  liczby, powody opóźnień. To one najczęściej giną przy streszczaniu.

PROPORCJONALNOŚĆ — NAJWAŻNIEJSZA ZASADA:
- Długość notatki ma odpowiadać ilości treści w nagraniu. Z dwóch zdań nie da
  się zrobić raportu i NIE WOLNO próbować.
- Bardzo krótkie nagranie (1-3 zdania, jedna sprawa, zero uzasadnienia) →
  wypełnij TYLKO opis i zadania.
  Wszystkie pozostałe sekcje zostaw puste: []. To jest poprawna odpowiedź,
  a nie brak staranności.
- Sekcję wypełniaj tylko wtedy, gdy masz do niej treść, która NIE PADŁA już
  w innej sekcji. Pusta sekcja jest lepsza niż powtórzenie.

ZAKAZ POWTÓRZEŃ:
- Ta sama informacja nie może wystąpić w dwóch sekcjach. Jeśli coś jest
  w zadaniach, nie powtarzaj tego w decyzjach ani w kluczowych myślach.
  Jeśli opis mówi "spotkanie przełożone na czwartek", to NIE jest ani decyzja,
  ani termin do osobnego wypisania — to już zostało powiedziane.
- Nie parafrazuj opisu w innych sekcjach innymi słowami.

OGRANICZENIE:
- Nie rozwlekaj i nie dodawaj zdań, które nic nie wnoszą. Nie uzupełniaj
  informacji, których nie ma w transkrypcji — lepiej krótko niż zmyślone.

KATEGORIE:
- "Praca" - sprawy służbowe (klient, projekt, spotkanie, raport, deadline, szef, firma)
- "Dom" - sprawy prywatne (rodzina, zakupy, dom, wakacje, dziecko, małżonka)
- "Inne" - wszystko inne

WAŻNE:
- Jeśli brak danych w danej sekcji → pusta tablica: []
- Confidence to liczba 0-1 (pewność klasyfikacji kategorii)
- Rozróżniaj: decyzje = rozstrzygnięte w nagraniu, otwarte_watki = zawisło
  w nagraniu bez odpowiedzi. Obie sekcje opisują to, co PADŁO — nie to, co
  dałoby się jeszcze zapytać
- Zadanie to AKCJA do wykonania, nie obserwacja
- Przy oznaczonych rozmówcach zachowaj ich etykiety dokładnie tak, jak
  występują w transkrypcji
- Znaczniki czasu bierz z transkrypcji, nie wymyślaj ich
- W punktach bloków pisz, KTO co powiedział, używając etykiet z transkrypcji:
  "Rozmówca 1 zauważył, że...", "Rozmówca 2 zasugerowała...".
  NIE przypisuj imion, nawet jeśli padają w rozmowie — etykiety są neutralne
  i nie mylą osób
"""



def validate_config():
    """Sprawdza czy wszystkie wymagane zmienne są ustawione"""
    errors = []

    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN nie jest ustawiony w .env")

    if not ALLOWED_USER_IDS:
        errors.append("ALLOWED_USER_IDS nie jest ustawiony w .env")

    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY nie jest ustawiony w .env")

    if errors:
        raise ValueError("Błędy konfiguracji:\n" + "\n".join(errors))

    return True
