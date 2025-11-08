# Importă funcția care creează aplicația și instanța db
from app import create_app, db
from app.models import Subject

# Creează o instanță a aplicației
app = create_app()

# AICI ESTE MAGIA:
# Rulează codul "în interiorul" contextului aplicației
with app.app_context():
    # Acum poți lucra cu baza de date

    # Verifică dacă materiile există deja
    if not Subject.query.filter_by(name="Matematica").first():
        matematica = Subject(name="Matematica")
        db.session.add(matematica)
        print("Adaugat Matematica")

    if not Subject.query.filter_by(name="Romana").first():
        romana = Subject(name="Romana")
        db.session.add(romana)
        print("Adaugat Romana")

    if not Subject.query.filter_by(name="Biologie").first():
        biologie = Subject(name="Biologie")
        db.session.add(biologie)
        print("Adaugat Biologie")

    # Salvează modificările
    try:
        db.session.commit()
        print("Materiile au fost salvate cu succes!")
    except Exception as e:
        db.session.rollback()
        print(f"A aparut o eroare: {e}")