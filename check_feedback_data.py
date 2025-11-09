from app import create_app, db
from app.models import Submission, Feedback, AIReport, Student, Assignment

app = create_app()

with app.app_context():
    print("\n" + "=" * 70)
    print("🔍 VERIFICARE DATE FEEDBACK")
    print("=" * 70)

    feedbacks = Feedback.query.all()

    if not feedbacks:
        print("\n⚠️  NICIUN FEEDBACK ÎN BAZA DE DATE!")
    else:
        for fb in feedbacks:
            print(f"\n📝 Feedback ID: {fb.id}")
            print(f"  - Submission ID: {fb.submission_id}")

            if fb.submission:
                sub = fb.submission
                print(f"  - Student: {sub.student.user.name if sub.student else 'N/A'}")
                print(f"  - Assignment: {sub.assignment.title if sub.assignment else 'N/A'}")
                print(f"  - Răspuns elev: {sub.content[:100] if sub.content else 'GOL'}...")

            print(f"  - Notă: {fb.grade}/10")
            print(f"  - Feedback text: {fb.feedback_text[:100]}...")

            # Verifică dacă există raport AI
            ai_report = AIReport.query.filter_by(feedback_id=fb.id).first()
            if ai_report:
                print(f"  - ✅ Are raport AI (ID: {ai_report.id})")
                print(f"    Summary: {ai_report.summary[:80]}...")
            else:
                print(f"  - ❌ NU are raport AI generat")

    print("\n" + "=" * 70)