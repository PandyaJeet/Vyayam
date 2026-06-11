# VYAYAM STRENGTH TRAINING SYSTEM

Professional AI-Powered Physiotherapy & Strength Training Platform with Real-Time Form Tracking

## ⚡ Current Architecture (2026-06 — read this first)

The sections below describe the ORIGINAL legacy 8-dimension flow, kept
for history. The live product is the **V1 engine + athlete tier +
B2B2C therapist console**:

| Layer | Files | Notes |
|---|---|---|
| V1 prescription engine | `strength_app/v1_prescription_engine.py`, `v1_safety_logic.py`, `v1_constants.py` | `generate_v1_session(patient)` is the single entry point. 20 physio principles, periodisation, red-flag filtering, hormonal/sex/age modifiers, pain follow-through (DA-F3). |
| Self-serve patient flow | `v1_onboarding_views.py` (10-screen assessment), `v1_session_views.py`, `v1_progress_views.py`, `v1_nutrition_*` | Client-side MediaPipe scoring lives in `templates/strength_app/v1_exercise_execute.html`. |
| Athlete tier (football) | `v1_football_views.py`, `v1_football_constants.py`, `v1_coach_views.py` | Coach squad dashboard + override; framing is training-readiness, never clinical (rule R1). ACWR formally excluded (rule R2). |
| B2B2C therapist console | `therapist_app/` | Therapist-managed patients, prescriptions, session logs, PDF reports. Legitimately clinical language. |
| Exercise data layers | `v1_progression_chains.py` (V1 chains), `exercise_content*.py`, `equipment_routing.py`, `red_flag_map.py`, `warmup_library.py` | `exercise_tags.py` serves ONLY the legacy gate-test dosage path. |
| CV exercise modules | `exercise_system/exercises/*.py` (264), `exercise_system/core/` | Driven by the desktop headless runner; web flow uses client-side JS. Ideal-trajectory harness: `tests/clinical_audit/generators/trajectory_generator.py`. |
| Legacy engine | `strength_app/backend/` (in-memory), `utils.py` bridge, gate-test routes in `views.py` | Pre-V1 system, still reachable through the legacy gate-test flow. |

Audit history: `AUDIT_FIXES_CHANGELOG.md`, `GROUP1..6_AUDIT.md`,
`DEEP_AUDIT_REPORT.md` (2026-06), `DECISIONS_NEEDED.md`.

## 📋 Overview

VYAYAM is a complete Django-based strength training system that combines:
- **8 Clusteral Dimension Assessment** (Age, Fitness, Goals, Biomechanics, Pain Tolerance, Lifestyle, Compliance, Timeline)
- **Gate Testing** across 4 exercise categories
- **AI Auto-Prescription Engine** with therapist manual override option
- **Real-Time Form Tracking** (Green/Yellow/Red rep classification)
- **Daily Feedback Loop** with automatic progression/regression
- **Professional Progress Reports** compatible with health management systems

## 🏗️ Project Structure

```
vyayam_django/
├── manage.py                       # Django management script
│
├── vyayam_project/                 # Django project configuration
│   ├── __init__.py
│   ├── settings.py                 # Django settings
│   ├── urls.py                     # Main URL routing
│   ├── wsgi.py                     # WSGI configuration
│   └── asgi.py                     # ASGI configuration
│
└── strength_app/                   # Main Django app
    ├── __init__.py
    ├── models.py                   # Django ORM models
    ├── views.py                    # View logic
    ├── urls.py                     # App URL patterns
    ├── forms.py                    # Form definitions
    ├── admin.py                    # Admin interface config
    ├── utils.py                    # Integration with backend
    │
    ├── backend/                    # Backend logic (Pure Python)
    │   ├── __init__.py
    │   ├── database_schema.py      # Data structures (dataclasses)
    │   ├── gate_test_system.py     # Gate testing logic
    │   ├── prescription_engine.py  # Prescription generation
    │   ├── form_tracking.py        # Form analysis & rep counting
    │   ├── session_execution.py    # Workout session execution
    │   ├── report_generator.py     # Professional report generation
    │   └── main_coordinator.py     # System orchestration
    │
    ├── templates/                  # HTML templates
    │   └── strength_app/
    │       ├── base.html
    │       ├── home.html
    │       ├── register.html
    │       ├── login.html
    │       ├── dashboard.html
    │       ├── gate_testing.html
    │       ├── gate_test_results.html
    │       ├── prescription.html
    │       ├── prescription_display.html
    │       ├── daily_workout.html
    │       ├── workout_complete.html
    │       ├── progress_reports.html
    │       └── view_report.html
    │
    └── static/                     # Static files (CSS, JS, images)
        └── strength_app/
            ├── css/
            └── js/
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip
- Virtual environment (recommended)

### Installation

1. **Create and activate virtual environment:**
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate
```

2. **Install dependencies:**
```bash
pip install django==4.2
```

3. **Navigate to project directory:**
```bash
cd vyayam_django
```

4. **Run migrations:**
```bash
python manage.py makemigrations
python manage.py migrate
```

5. **Create superuser (for admin access):**
```bash
python manage.py createsuperuser
```

6. **Run development server:**
```bash
python manage.py runserver
```

7. **Access the application:**
- Main app: http://127.0.0.1:8000/
- Admin panel: http://127.0.0.1:8000/admin/

## 📚 System Architecture

### Backend Logic (Pure Python)

The `backend/` directory contains the core logic separated from Django:

1. **database_schema.py**: Data structures using Python dataclasses
   - PatientProfile (8 clusteral dimensions)
   - GateTestResult, GateTestSession
   - WorkoutSession, ExerciseData, RepData, SetData
   - ProgressReport, WeeklyProgress
   - Enums: CapabilityLevel, FormQuality, ExerciseCategory

2. **gate_test_system.py**: Gate testing engine
   - Classifies capability: CANNOT_DO / STRUGGLING / MANAGEABLE / EASY
   - Determines starting prescription (sets, reps, phase)
   - Handles "too easy" advancement flow

3. **prescription_engine.py**: AI prescription logic
   - Exercise progression ladders (from easiest to hardest)
   - AI Auto-Prescription mode
   - Therapist Manual Override mode
   - Automatic adjustment for progression/regression

4. **form_tracking.py**: Real-time form analysis
   - Rep-by-rep form scoring (angle, stability, tempo)
   - Green/Yellow/Red classification
   - Practice mode when form is poor
   - Voice guidance system

5. **session_execution.py**: Workout session execution
   - Daily feedback loop
   - Automatic progression/regression logic
   - Comfort-based adjustments

6. **report_generator.py**: Professional report generation
   - Weekly summaries
   - Exercise progressions
   - Volume analysis
   - Clinical notes format

### Django Integration

- **models.py**: Django ORM models mirroring backend data structures
- **utils.py**: Bridge between Django and backend logic
- **views.py**: HTTP request handlers
- **forms.py**: Patient registration and feedback forms

## 🎯 Key Features

### 8 Clusteral Dimensions

The system assesses patients across 8 critical dimensions:

1. **Age**: Automatically adjusted thresholds
2. **Fitness Level**: Gate test determines capability per exercise category
3. **Goals**: Functional / Athletic / Rehabilitation
4. **Biomechanics**: Inferred from occupation and activity pattern
5. **Pain/Difficulty Tolerance**: Measured during gate test
6. **Lifestyle**: Sedentary / Active / Very Active
7. **Compliance**: Proven through gate test completion
8. **Timeline**: No Rush / Moderate / Urgent

### Gate Testing

Four exercise categories tested:
- **Lower Body**: Squat variations
- **Posterior Chain**: Deadlift variations
- **Upper Body**: Rowing variations
- **Cardio**: Endurance capacity

Results classify into:
- **CANNOT_DO**: Can't perform safely → Phase 0 (foundation work)
- **STRUGGLING**: Can do but difficult → Phase 1 Low (2×6)
- **MANAGEABLE**: Moderate effort → Phase 1 Standard (3×10)
- **EASY**: Can do easily → Phase 1 High (3×15)

### AI Auto-Prescription

Based on gate test results:
1. **Stretching**: 5 exercises, hold-based
2. **Strength**: Personalized progression for each category
3. **Cardio**: Based on capability level
4. **Accessories**: Added based on overall fitness

Prescription adjusts automatically based on:
- Not comfortable for 2 days → Go back 1 level
- Comfortable for whole week + threshold met → Advance 1 level
- Form failure → Practice mode → Possible regression

### Form Tracking

Real-time analysis provides:
- **Form Score**: (angle_accuracy × 0.5) + (stability × 0.3) + (tempo_control × 0.2)
- **GREEN** (≥75%): Good form, rep counted
- **YELLOW** (50-74%): Poor form, rep not counted
- **RED** (<50%): Dangerous form, stop set immediately

### Progress Reports

Professional physiotherapy reports include:
- Patient information & assessment summary
- Week-by-week comparison
- Exercise progressions/regressions
- Volume analysis (reps per week per exercise)
- Form improvement metrics
- Adherence rates
- Clinical recommendations

## 🔧 Configuration

### Prescription Modes

**AI Auto (Default):**
- System generates prescription from gate test
- Automatically progresses/regresses based on feedback
- No therapist needed

**Therapist Manual:**
- Licensed therapist creates custom prescription
- System tracks execution and provides reports
- AI suggestions available to therapist

### Form Tracking Configuration

In `backend/form_tracking.py`:
```python
self.green_threshold = 0.75  # 75%
self.yellow_threshold = 0.50  # 50%
```

### Progression Thresholds

In `backend/prescription_engine.py`:
- Threshold to advance: 15 reps × 3 sets at current level
- Regression trigger: 2 consecutive uncomfortable days
- Advancement trigger: 7 consecutive comfortable days + threshold met

## 📊 Database Models

### Main Models

1. **PatientProfile**: Complete patient data with 8 dimensions
2. **GateTestResult**: Individual gate test results per category
3. **WorkoutSession**: Complete daily workout with all exercises
4. **ExerciseExecution**: Individual exercise data within a session
5. **TherapistProfile**: Licensed therapist information
6. **TherapistPrescription**: Manual prescriptions from therapists
7. **ExerciseProgressionState**: Tracking progression per exercise category
8. **ProgressReport**: Professional reports for health records

### Relationships

```
PatientProfile (1) ─── (many) GateTestResult
PatientProfile (1) ─── (many) WorkoutSession
WorkoutSession (1) ─── (many) ExerciseExecution
PatientProfile (1) ─── (many) ProgressReport
TherapistProfile (1) ─── (many) PatientProfile
TherapistProfile (1) ─── (many) TherapistPrescription
```

## 🧪 Testing

Run backend logic tests:
```bash
cd strength_app/backend
python gate_test_system.py
python prescription_engine.py
python form_tracking.py
python session_execution.py
python report_generator.py
python main_coordinator.py
```

Each backend module has a `__main__` block with demo usage.

## 📝 API Endpoints

| URL | View | Description |
|-----|------|-------------|
| `/` | home | Landing page |
| `/register/` | register_patient | New patient registration |
| `/login/` | patient_login | Patient login |
| `/dashboard/` | dashboard | Patient dashboard |
| `/gate-testing/` | gate_testing | Conduct gate tests |
| `/gate-test-results/` | gate_test_results | View gate test results |
| `/prescription/` | prescription | Generate prescription |
| `/daily-workout/` | daily_workout | Execute workout session |
| `/progress-reports/` | progress_reports | List all reports |
| `/generate-report/` | generate_report | Create new report |
| `/view-report/<id>/` | view_report | View specific report |
| `/download-report/<id>/` | download_report | Download report as text |

## 🎨 Frontend

Built with:
- Bootstrap 5 for UI components
- Font Awesome for icons
- Responsive design for mobile/tablet/desktop

Templates use Django's template inheritance:
- `base.html`: Base layout with navbar and footer
- Specific pages extend base template

## 🔐 Security

Current setup is for development. For production:
1. Change SECRET_KEY in settings.py
2. Set DEBUG = False
3. Configure ALLOWED_HOSTS
4. Use proper database (PostgreSQL recommended)
5. Add HTTPS
6. Implement proper authentication system
7. Add CSRF protection for all forms
8. Sanitize user inputs
9. Implement rate limiting
10. Add logging and monitoring

## 🚧 TODO / Future Enhancements

### Phase 2 Features:
- [ ] Computer vision integration for actual form tracking
- [ ] Video demos for each exercise
- [ ] Mobile app (React Native)
- [ ] Real-time voice feedback
- [ ] Integration with wearables (heart rate, etc.)
- [ ] Social features (challenges, leaderboards)
- [ ] Exercise library expansion
- [ ] Advanced analytics dashboard

### Backend Improvements:
- [ ] Replace SQLite with PostgreSQL
- [ ] Add Redis for caching
- [ ] Implement Celery for async tasks
- [ ] Add WebSocket for real-time updates
- [ ] Create REST API with Django REST Framework
- [ ] Add comprehensive test suite
- [ ] Docker containerization
- [ ] CI/CD pipeline

## 📄 License

Proprietary - All Rights Reserved

## 👥 Authors

VYAYAM Strength Training Development Team

## 📞 Support

For support or questions, please contact your system administrator.

---

**Version**: 1.0.0  
**Last Updated**: February 2024
