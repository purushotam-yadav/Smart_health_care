
import os
from flask import Flask, jsonify
from supabase import create_client
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask import render_template
from flask import render_template, request, redirect, url_for, flash
load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials .env file mein missing hain")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.route("/")
def home():
    return jsonify({
        "message": "Smart Health Care System Backend Running"
    })


@app.route("/test-db")
def test_db():
    result = supabase.table("patients").select(
        "patient_id, full_name"
    ).limit(5).execute()

    return jsonify({
        "message": "Supabase connection successful",
        "patients": result.data
    })


# GET: View all patients
@app.route("/patients", methods=["GET"])
def get_patients():
    try:
        result = (
            supabase.table("patients")
            .select("*")
            .order("patient_id")
            .execute()
        )

        return jsonify(result.data), 200

    except Exception as e:
        app.logger.exception("Could not fetch patients")
        return jsonify({"error": "Could not fetch patients"}), 500


# POST: Register a new patient
@app.route("/patients", methods=["POST"])
def add_patient():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400

    full_name = data.get("full_name")
    if not isinstance(full_name, str) or not full_name.strip():
        return jsonify({"error": "full_name is required"}), 400

    age = data.get("age")
    if age is not None:
        if type(age) is not int or not 0 <= age <= 120:
            return jsonify({"error": "age must be an integer from 0 to 120"}), 400

    allowed_fields = ["full_name", "age", "gender", "phone", "email"]
    patient_data = {
        key: data[key]
        for key in allowed_fields
        if key in data
    }
    patient_data["full_name"] = full_name.strip()

    try:
        result = (
            supabase.table("patients")
            .insert(patient_data)
            .execute()
        )

        return jsonify({
            "message": "Patient registered successfully",
            "patient": result.data[0]
        }), 201

    except Exception:
        app.logger.exception("Could not register patient")
        return jsonify({"error": "Could not register patient"}), 500


# PUT: Update an existing patient
@app.route("/patients/<int:patient_id>", methods=["PUT"])
def update_patient(patient_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({"error": "JSON object with updates required"}), 400

    allowed_fields = ["full_name", "age", "gender", "phone", "email"]

    if not set(data).issubset(allowed_fields):
        return jsonify({"error": "Invalid field provided"}), 400

    if "full_name" in data:
        if not isinstance(data["full_name"], str) or not data["full_name"].strip():
            return jsonify({"error": "full_name cannot be empty"}), 400
        data["full_name"] = data["full_name"].strip()

    if "age" in data and data["age"] is not None:
        if type(data["age"]) is not int or not 0 <= data["age"] <= 120:
            return jsonify({"error": "Invalid age"}), 400

    try:
        result = (
            supabase.table("patients")
            .update(data)
            .eq("patient_id", patient_id)
            .execute()
        )

        if not result.data:
            return jsonify({"error": "Patient not found"}), 404

        return jsonify({
            "message": "Patient updated successfully",
            "patient": result.data[0]
        }), 200

    except Exception:
        app.logger.exception("Could not update patient")
        return jsonify({"error": "Could not update patient"}), 500


# DELETE: Delete a patient
@app.route("/patients/<int:patient_id>", methods=["DELETE"])
def delete_patient(patient_id):
    try:
        # Check whether the patient exists
        existing = (
            supabase.table("patients")
            .select("patient_id")
            .eq("patient_id", patient_id)
            .execute()
        )

        if not existing.data:
            return jsonify({"error": "Patient not found"}), 404

        (
            supabase.table("patients")
            .delete()
            .eq("patient_id", patient_id)
            .execute()
        )

        return jsonify({
            "message": "Patient deleted successfully",
            "patient_id": patient_id
        }), 200

    except Exception:
        app.logger.exception("Could not delete patient")
        return jsonify({"error": "Could not delete patient"}), 500


# GET: View all doctors
@app.route("/doctors", methods=["GET"])
def get_doctors():
    try:
        result = (
            supabase.table("doctors")
            .select("*")
            .order("doctor_id")
            .execute()
        )
        return jsonify(result.data), 200

    except Exception:
        app.logger.exception("Could not fetch doctors")
        return jsonify({"error": "Could not fetch doctors"}), 500


# POST: Add a new doctor
@app.route("/doctors", methods=["POST"])
def add_doctor():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400

    name = data.get("full_name")
    specialization = data.get("specialization")

    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "full_name is required"}), 400

    if not isinstance(specialization, str) or not specialization.strip():
        return jsonify({"error": "specialization is required"}), 400

    allowed = [
        "full_name", "specialization", "phone",
        "email", "consultation_fee", "available"
    ]

    if not set(data).issubset(allowed):
        return jsonify({"error": "Invalid field provided"}), 400

    fee = data.get("consultation_fee")
    if fee is not None:
        if isinstance(fee, bool) or not isinstance(fee, (int, float)) or fee < 0:
            return jsonify({"error": "Invalid consultation fee"}), 400

    if "available" in data and not isinstance(data["available"], bool):
        return jsonify({"error": "available must be true or false"}), 400

    doctor_data = dict(data)
    doctor_data["full_name"] = name.strip()
    doctor_data["specialization"] = specialization.strip()

    try:
        result = (
            supabase.table("doctors")
            .insert(doctor_data)
            .execute()
        )

        return jsonify({
            "message": "Doctor added successfully",
            "doctor": result.data[0]
        }), 201

    except Exception:
        app.logger.exception("Could not add doctor")
        return jsonify({"error": "Could not add doctor. Check the data and email uniqueness."}), 500


# GET: View appointments with patient and doctor details
@app.route("/appointments", methods=["GET"])
def get_appointments():
    try:
        result = (
            supabase.table("appointments")
            .select(
                "*, "
                "patients!fk_patient(full_name), "
                "doctors!fk_doctor(full_name, specialization)"
            )
            .order("appointment_id")
            .execute()
        )

        return jsonify(result.data), 200

    except Exception:
        app.logger.exception("Could not fetch appointments")
        return jsonify({"error": "Could not fetch appointments"}), 500


# POST: Book a new appointment
@app.route("/appointments", methods=["POST"])
def add_appointment():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400

    allowed = [
        "patient_id", "doctor_id", "appointment_date",
        "appointment_time", "reason"
    ]

    if not set(data).issubset(allowed):
        return jsonify({"error": "Invalid field provided"}), 400

    patient_id = data.get("patient_id")
    doctor_id = data.get("doctor_id")
    appointment_date = data.get("appointment_date")
    appointment_time = data.get("appointment_time")

    if type(patient_id) is not int or patient_id <= 0:
        return jsonify({"error": "Valid patient_id is required"}), 400

    if type(doctor_id) is not int or doctor_id <= 0:
        return jsonify({"error": "Valid doctor_id is required"}), 400

    if not isinstance(appointment_date, str) or not isinstance(appointment_time, str):
        return jsonify({
            "error": "appointment_date and appointment_time are required"
        }), 400

    from datetime import date, time

    try:
        date.fromisoformat(appointment_date)
        time.fromisoformat(appointment_time)
    except ValueError:
        return jsonify({
            "error": "Use date YYYY-MM-DD and time HH:MM"
        }), 400

    appointment_data = {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "status": "Pending"
    }

    reason = data.get("reason")
    if reason is not None:
        if not isinstance(reason, str):
            return jsonify({"error": "reason must be text"}), 400
        appointment_data["reason"] = reason

    try:
        result = (
            supabase.table("appointments")
            .insert(appointment_data)
            .execute()
        )

        return jsonify({
            "message": "Appointment booked successfully",
            "appointment": result.data[0]
        }), 201

    except Exception:
        app.logger.exception("Could not book appointment")
        return jsonify({
            "error": "Could not book appointment. Verify patient and doctor IDs."
        }), 500


@app.route("/dashboard")
def dashboard():
    try:
        patients = (
            supabase.table("patients")
            .select("patient_id")
            .execute()
        )

        doctors = (
            supabase.table("doctors")
            .select("doctor_id")
            .execute()
        )

        appointments = (
            supabase.table("appointments")
            .select("appointment_id, status")
            .execute()
        )

        stats = {
            "total_patients": len(patients.data),
            "total_doctors": len(doctors.data),
            "total_appointments": len(appointments.data),
            "pending_appointments": sum(
                1 for a in appointments.data
                if a["status"] == "Pending"
            )
        }

        return render_template(
            "dashboard.html",
            stats=stats
        )

    except Exception:
        app.logger.exception("Dashboard loading failed")
        return "Dashboard load nahi ho saka. Server terminal check karo.", 500


@app.route("/web/patients", methods=["GET", "POST"])
def patients_page():
    message = None
    message_type = "success"

    # Register patient — existing functionality preserved
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        age_text = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()

        if not full_name or not age_text:
            message = "Patient name aur age required hain."
            message_type = "error"
        else:
            try:
                age = int(age_text)

                if not 0 <= age <= 120:
                    message = "Age 0 se 120 ke beech honi chahiye."
                    message_type = "error"
                else:
                    patient_data = {
                        "full_name": full_name,
                        "age": age,
                        "gender": gender or None,
                        "phone": phone or None,
                        "email": email or None
                    }

                    supabase.table("patients").insert(
                        patient_data
                    ).execute()

                    return redirect(
                        url_for("patients_page", registered="1")
                    )

            except ValueError:
                message = "Age mein valid number enter karo."
                message_type = "error"
            except Exception:
                message = (
                    "Patient save nahi hua. Database settings "
                    "aur input check karo."
                )
                message_type = "error"

    # Search, filter and pagination settings
    search = request.args.get("q", "").strip()[:100]
    gender_filter = request.args.get("gender", "").strip()

    if gender_filter not in ["Male", "Female", "Other"]:
        gender_filter = ""

    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1

    per_page = 10
    total_patients = 0
    total_pages = 1
    patients = []

    try:
        # Build Supabase query
        query = supabase.table("patients").select(
            "*", count="exact"
        )

        # Search by name, phone or email
        if search:
            # Remove characters that can interfere with
            # the PostgREST OR filter syntax
            safe_search = (
                search.replace(",", "")
                .replace("(", "")
                .replace(")", "")
            )

            if safe_search:
                pattern = f"%{safe_search}%"
                query = query.or_(
                    f"full_name.ilike.{pattern},"
                    f"phone.ilike.{pattern},"
                    f"email.ilike.{pattern}"
                )

        # Gender filter
        if gender_filter:
            query = query.eq("gender", gender_filter)

        # Count matching records and fetch one page
        query = query.order("patient_id", desc=True)

        start = (page - 1) * per_page
        end = start + per_page - 1

        result = query.range(start, end).execute()

        total_patients = result.count or 0
        total_pages = max(
            1,
            (total_patients + per_page - 1) // per_page
        )

        # Keep page number within valid range
        if page > total_pages:
            page = total_pages
            start = (page - 1) * per_page
            end = start + per_page - 1
            result = query.range(start, end).execute()

        patients = result.data or []

    except Exception:
        app.logger.exception("Could not load patient records")
        message = "Patients load nahi ho paaye. Database check karo."
        message_type = "error"

    # Existing success and error messages
    if request.args.get("registered") == "1":
        message = "Patient successfully register ho gaya!"
        message_type = "success"
    elif request.args.get("updated") == "1":
        message = "Patient successfully updated!"
        message_type = "success"
    elif request.args.get("deleted") == "1":
        message = "Patient successfully deleted!"
        message_type = "success"
    elif request.args.get("delete_error") == "1":
        message = (
            "Patient delete nahi hua. Ho sakta hai uski "
            "appointment linked ho."
        )
        message_type = "error"

    return render_template(
        "patients.html",
        patients=patients,
        message=message,
        message_type=message_type,
        search=search,
        gender_filter=gender_filter,
        page=page,
        per_page=per_page,
        total_patients=total_patients,
        total_pages=total_pages
    )


@app.route("/web/patients/edit/<int:patient_id>", methods=["GET", "POST"])
def edit_patient_page(patient_id):
    message = None
    message_type = "error"

    try:
        result = (
            supabase.table("patients")
            .select("*")
            .eq("patient_id", patient_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []

        if not rows:
            return "Patient not found", 404

        patient = rows[0]

    except Exception:
        return "Patient load nahi ho paaya.", 500

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        age_text = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()

        if not full_name or not age_text:
            message = "Patient name aur age required hain."

        else:
            try:
                age = int(age_text)

                if not 0 <= age <= 120:
                    message = "Age 0 se 120 ke beech honi chahiye."
                else:
                    updated_data = {
                        "full_name": full_name,
                        "age": age,
                        "gender": gender or None,
                        "phone": phone or None,
                        "email": email or None
                    }

                    supabase.table("patients").update(
                        updated_data
                    ).eq("patient_id", patient_id).execute()

                    return redirect(
                        url_for("patients_page", updated="1")
                    )

            except ValueError:
                message = "Age mein valid number enter karo."

            except Exception:
                message = "Patient update nahi hua. Input aur database check karo."

        # Validation fail ho to form mein naye entered values dikhayein
        patient = {
            "patient_id": patient_id,
            "full_name": full_name,
            "age": age_text,
            "gender": gender,
            "phone": phone,
            "email": email
        }

    return render_template(
        "edit_patient.html",
        patient=patient,
        message=message,
        message_type=message_type
    )


@app.route("/web/patients/delete/<int:patient_id>", methods=["POST"])
def delete_patient_page(patient_id):
    try:
        supabase.table("patients").delete().eq(
            "patient_id", patient_id
        ).execute()

        return redirect(
            url_for("patients_page", deleted="1")
        )

    except Exception:
        # Patient ki appointment linked ho sakti hai
        return redirect(
            url_for("patients_page", delete_error="1")
        )

@app.route("/web/doctors", methods=["GET", "POST"])

@app.route("/web/doctors", methods=["GET", "POST"])
def doctors_page():
    message = None
    message_type = "success"

    # Doctor registration — existing functionality
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        specialization = request.form.get("specialization", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        fee_text = request.form.get("consultation_fee", "").strip()
        available = request.form.get("available") == "true"

        if not full_name or not specialization:
            message = "Doctor name aur specialization required hain."
            message_type = "error"
        else:
            try:
                fee = float(fee_text) if fee_text else 0

                if fee < 0:
                    message = "Consultation fee negative nahi ho sakti."
                    message_type = "error"
                else:
                    doctor_data = {
                        "full_name": full_name,
                        "specialization": specialization,
                        "phone": phone or None,
                        "email": email or None,
                        "consultation_fee": fee,
                        "available": available
                    }

                    supabase.table("doctors").insert(
                        doctor_data
                    ).execute()

                    return redirect(
                        url_for("doctors_page", registered="1")
                    )

            except ValueError:
                message = "Consultation fee valid number honi chahiye."
                message_type = "error"
            except Exception:
                message = (
                    "Doctor register nahi hua. Email duplicate "
                    "ya database error check karo."
                )
                message_type = "error"

    # Search, availability filter and pagination
    search = request.args.get("q", "").strip()[:100]
    availability_filter = request.args.get(
        "availability", ""
    ).strip().lower()

    if availability_filter not in ("available", "unavailable"):
        availability_filter = ""

    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    per_page = 10

    try:
        query = supabase.table("doctors").select("*", count="exact")

        if search:
            # Escape PostgREST filter punctuation in user input
            safe_search = (
                search.replace("\\", "")
                .replace(",", "")
                .replace("(", "")
                .replace(")", "")
            )
            pattern = f"%{safe_search}%"

            query = query.or_(
                f"full_name.ilike.{pattern},"
                f"specialization.ilike.{pattern},"
                f"phone.ilike.{pattern},"
                f"email.ilike.{pattern}"
            )

        if availability_filter == "available":
            query = query.eq("available", True)
        elif availability_filter == "unavailable":
            query = query.eq("available", False)

        query = query.order("doctor_id", desc=True)

        # Find total records before applying pagination
        count_result = query.execute()
        total_doctors = count_result.count or 0
        total_pages = max(
            1, (total_doctors + per_page - 1) // per_page
        )

        page = min(page, total_pages)
        start = (page - 1) * per_page

        result = query.range(
            start, start + per_page - 1
        ).execute()

        doctors = result.data or []

    except Exception:
        doctors = []
        total_doctors = 0
        total_pages = 1
        message = "Doctors load nahi ho paaye. Database connection check karo."
        message_type = "error"

    # Success and action messages
    if request.args.get("registered") == "1":
        message = "Doctor successfully register ho gaya."
        message_type = "success"
    elif request.args.get("updated") == "1":
        message = "Doctor details successfully update ho gayi."
        message_type = "success"
    elif request.args.get("deleted") == "1":
        message = "Doctor successfully delete ho gaya."
        message_type = "success"
    elif request.args.get("delete_error") == "1":
        message = (
            "Doctor delete nahi ho saka. Ho sakta hai uski "
            "appointments linked hon."
        )
        message_type = "error"

    return render_template(
        "doctors.html",
        doctors=doctors,
        message=message,
        message_type=message_type,
        search=search,
        availability_filter=availability_filter,
        page=page,
        per_page=per_page,
        total_doctors=total_doctors,
        total_pages=total_pages
    )
@app.route("/web/doctors/edit/<int:doctor_id>", methods=["GET", "POST"])
def edit_doctor_page(doctor_id):
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        specialization = request.form.get("specialization", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        fee_text = request.form.get("consultation_fee", "").strip()
        available = request.form.get("available") == "true"

        try:
            fee = float(fee_text) if fee_text else 0
            
            supabase.table("doctors").update({
                "full_name": full_name,
                "specialization": specialization,
                "phone": phone or None,
                "email": email or None,
                "consultation_fee": fee,
                "available": available
            }).eq("doctor_id", doctor_id).execute()

            return redirect(url_for("doctors_page", updated="1"))
        except Exception:
            app.logger.exception("Could not update doctor")
            return "Could not update doctor", 500

    try:
        result = supabase.table("doctors").select("*").eq("doctor_id", doctor_id).execute()
        if not result.data:
            return "Doctor not found", 404
        return render_template("edit_doctor.html", doctor=result.data[0])
    except Exception:
        app.logger.exception("Could not fetch doctor for editing")
        return "Could not load edit page", 500


@app.route("/web/doctors/delete/<int:doctor_id>", methods=["POST"])
def delete_doctor_page(doctor_id):
    try:
        supabase.table("doctors").delete().eq(
            "doctor_id", doctor_id
        ).execute()

        return redirect(
            url_for("doctors_page", deleted="1")
        )

    except Exception:
        # Linked appointments ki wajah se deletion reject ho sakta hai
        return redirect(
            url_for("doctors_page", delete_error="1")
        )


@app.route("/web/appointments", methods=["GET", "POST"])
def appointments_page():
    message = None
    message_type = "success"

    # Book appointment — existing functionality preserved
    if request.method == "POST":
        patient_id = request.form.get("patient_id", "").strip()
        doctor_id = request.form.get("doctor_id", "").strip()
        appointment_date = request.form.get("appointment_date", "").strip()
        appointment_time = request.form.get("appointment_time", "").strip()
        reason = request.form.get("reason", "").strip()

        try:
            if not all([
                patient_id, doctor_id,
                appointment_date, appointment_time
            ]):
                raise ValueError("Required fields fill karo.")

            patient_id = int(patient_id)
            doctor_id = int(doctor_id)

            if patient_id < 1 or doctor_id < 1:
                raise ValueError("Patient aur doctor select karo.")

            from datetime import date, time
            date.fromisoformat(appointment_date)
            time.fromisoformat(appointment_time)

            patient_result = (
                supabase.table("patients")
                .select("patient_id")
                .eq("patient_id", patient_id)
                .limit(1)
                .execute()
            )

            doctor_result = (
                supabase.table("doctors")
                .select("doctor_id, available")
                .eq("doctor_id", doctor_id)
                .limit(1)
                .execute()
            )

            if not patient_result.data:
                raise ValueError("Selected patient nahi mila.")

            if not doctor_result.data:
                raise ValueError("Selected doctor nahi mila.")

            if not doctor_result.data[0]["available"]:
                raise ValueError("Ye doctor abhi available nahi hai.")

            appointment_data = {
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
                "reason": reason or None,
                "status": "Pending"
            }

            supabase.table("appointments").insert(
                appointment_data
            ).execute()

            return redirect(
                url_for("appointments_page", booked="1")
            )

        except ValueError as exc:
            message = str(exc)
            message_type = "error"

        except Exception:
            message = (
                "Appointment save nahi hui. Database aur input check karo."
            )
            message_type = "error"

    # Load patients, available doctors and appointments
    try:
        patients_result = (
            supabase.table("patients")
            .select("patient_id, full_name")
            .order("full_name")
            .execute()
        )

        doctors_result = (
            supabase.table("doctors")
            .select("doctor_id, full_name, specialization")
            .eq("available", True)
            .order("full_name")
            .execute()
        )

        appointments_result = (
            supabase.table("appointments")
            .select(
                "*, "
                "patients!fk_patient(full_name), "
                "doctors!fk_doctor(full_name, specialization)"
            )
            .order("appointment_date", desc=True)
            .order("appointment_time", desc=True)
            .execute()
        )

        patients = patients_result.data or []
        doctors = doctors_result.data or []
        all_appointments = appointments_result.data or []

    except Exception:
        patients = []
        doctors = []
        all_appointments = []
        message = "Data load nahi hua. Database connection check karo."
        message_type = "error"

    # Search and status filter
    search = request.args.get("q", "").strip()[:100]
    status_filter = request.args.get("status", "").strip()

    allowed_statuses = {
        "Pending", "Confirmed", "Completed", "Cancelled"
    }

    if status_filter not in allowed_statuses:
        status_filter = ""

    filtered_appointments = []

    for appointment in all_appointments:
        patient = appointment.get("patients") or {}
        doctor = appointment.get("doctors") or {}

        searchable_text = " ".join([
            str(patient.get("full_name") or ""),
            str(doctor.get("full_name") or ""),
            str(appointment.get("reason") or "")
        ])

        if search and search.casefold() not in searchable_text.casefold():
            continue

        if status_filter and appointment.get("status") != status_filter:
            continue

        filtered_appointments.append(appointment)

    # Pagination: 10 appointments per page
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    per_page = 10
    total_appointments = len(filtered_appointments)
    total_pages = max(
        1, (total_appointments + per_page - 1) // per_page
    )

    page = min(page, total_pages)
    start = (page - 1) * per_page

    appointments = filtered_appointments[start:start + per_page]

    # Success and error messages
    if request.args.get("booked") == "1":
        message = "Appointment successfully booked!"
        message_type = "success"
    elif request.args.get("updated") == "1":
        message = "Appointment successfully updated!"
        message_type = "success"
    elif request.args.get("deleted") == "1":
        message = "Appointment successfully deleted!"
        message_type = "success"
    elif request.args.get("delete_error") == "1":
        message = "Appointment delete nahi hui. Database error check karo."
        message_type = "error"

    return render_template(
        "appointments.html",
        patients=patients,
        doctors=doctors,
        appointments=appointments,
        message=message,
        message_type=message_type,
        search=search,
        status_filter=status_filter,
        page=page,
        per_page=per_page,
        total_appointments=total_appointments,
        total_pages=total_pages
    )

@app.route(
    "/web/appointments/edit/<int:appointment_id>",
    methods=["GET", "POST"]
)
def edit_appointment_page(appointment_id):
    message = None
    message_type = "error"

    try:
        result = (
            supabase.table("appointments")
            .select("*")
            .eq("appointment_id", appointment_id)
            .limit(1)
            .execute()
        )

        rows = result.data or []

        if not rows:
            return "Appointment not found", 404

        appointment = rows[0]

        patients_result = (
            supabase.table("patients")
            .select("patient_id, full_name")
            .order("full_name")
            .execute()
        )

        doctors_result = (
            supabase.table("doctors")
            .select("doctor_id, full_name, specialization, available")
            .order("full_name")
            .execute()
        )

        patients = patients_result.data or []
        doctors = doctors_result.data or []

    except Exception:
        return "Appointment data load nahi hua.", 500

    if request.method == "POST":
        patient_id = request.form.get("patient_id", "").strip()
        doctor_id = request.form.get("doctor_id", "").strip()
        appointment_date = request.form.get("appointment_date", "").strip()
        appointment_time = request.form.get("appointment_time", "").strip()
        reason = request.form.get("reason", "").strip()
        status = request.form.get("status", "").strip()

        try:
            from datetime import date, time

            patient_id = int(patient_id)
            doctor_id = int(doctor_id)

            if not appointment_date or not appointment_time:
                raise ValueError("Date aur time required hain.")

            date.fromisoformat(appointment_date)
            time.fromisoformat(appointment_time)

            if status not in [
                "Pending", "Confirmed", "Completed", "Cancelled"
            ]:
                raise ValueError("Invalid appointment status.")

            patient_result = (
                supabase.table("patients")
                .select("patient_id")
                .eq("patient_id", patient_id)
                .limit(1)
                .execute()
            )

            doctor_result = (
                supabase.table("doctors")
                .select("doctor_id, available")
                .eq("doctor_id", doctor_id)
                .limit(1)
                .execute()
            )

            if not patient_result.data:
                raise ValueError("Selected patient nahi mila.")

            if not doctor_result.data:
                raise ValueError("Selected doctor nahi mila.")

            if (
                not doctor_result.data[0]["available"]
                and doctor_id != appointment["doctor_id"]
            ):
                raise ValueError("Selected doctor available nahi hai.")

            updated_data = {
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
                "reason": reason or None,
                "status": status
            }

            supabase.table("appointments").update(
                updated_data
            ).eq("appointment_id", appointment_id).execute()

            return redirect(
                url_for("appointments_page", updated="1")
            )

        except ValueError as exc:
            message = str(exc)

        except Exception:
            message = "Appointment update nahi hui. Database check karo."

        # Form mein submitted values ko retain karo
        appointment = {
            **appointment,
            "patient_id": int(request.form["patient_id"])
                if request.form.get("patient_id", "").isdigit()
                else appointment["patient_id"],
            "doctor_id": int(request.form["doctor_id"])
                if request.form.get("doctor_id", "").isdigit()
                else appointment["doctor_id"],
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "reason": reason,
            "status": status
        }

    return render_template(
        "edit_appointment.html",
        appointment=appointment,
        patients=patients,
        doctors=doctors,
        message=message,
        message_type=message_type
    )
@app.route(
    "/web/appointments/delete/<int:appointment_id>",
    methods=["POST"]
)
def delete_appointment_page(appointment_id):
    try:
        supabase.table("appointments").delete().eq(
            "appointment_id", appointment_id
        ).execute()

        return redirect(
            url_for("appointments_page", deleted="1")
        )

    except Exception:
        return redirect(
            url_for("appointments_page", delete_error="1")
        )


# ==========================================
# PRESCRIPTIONS API
# ==========================================

@app.route("/prescriptions", methods=["GET", "POST"])
def prescriptions_api():

    # GET: View prescriptions
    if request.method == "GET":
        try:
            result = (
                supabase.table("prescriptions")
                .select(
                    "*, "
                    "patients!prescriptions_patient_id_fkey(full_name), "
                    "doctors!prescriptions_doctor_id_fkey(full_name), "
                    "prescription_medicines(*)"
                )
                .order("prescription_id", desc=True)
                .execute()
            )

            return jsonify({
                "success": True,
                "prescriptions": result.data or []
            }), 200

        except Exception as exc:
            app.logger.exception("Prescription list failed")
            return jsonify({
                "success": False,
                "error": "Prescriptions load nahi ho sake."
            }), 500

    # POST: Create prescription with medicines
    data = request.get_json(silent=True) or {}

    try:
        appointment_id = int(data.get("appointment_id", 0))
        diagnosis = (data.get("diagnosis") or "").strip()
        notes = (data.get("notes") or "").strip()
        medicines = data.get("medicines", [])

        if appointment_id < 1:
            return jsonify({
                "success": False,
                "error": "Valid appointment_id required hai."
            }), 400

        if not isinstance(medicines, list) or not medicines:
            return jsonify({
                "success": False,
                "error": "Kam se kam ek medicine add karo."
            }), 400

        # Verify appointment and get its patient and doctor
        appointment_result = (
            supabase.table("appointments")
            .select("appointment_id, patient_id, doctor_id")
            .eq("appointment_id", appointment_id)
            .limit(1)
            .execute()
        )

        if not appointment_result.data:
            return jsonify({
                "success": False,
                "error": "Appointment nahi mili."
            }), 404

        appointment = appointment_result.data[0]

        # One prescription per appointment
        existing = (
            supabase.table("prescriptions")
            .select("prescription_id")
            .eq("appointment_id", appointment_id)
            .limit(1)
            .execute()
        )

        if existing.data:
            return jsonify({
                "success": False,
                "error": "Is appointment ki prescription pehle se hai."
            }), 409

        # Validate medicine fields before inserting anything
        clean_medicines = []

        for medicine in medicines:
            if not isinstance(medicine, dict):
                return jsonify({
                    "success": False,
                    "error": "Medicine details ka format invalid hai."
                }), 400

            medicine_name = str(
                medicine.get("medicine_name") or ""
            ).strip()
            dosage = str(medicine.get("dosage") or "").strip()
            frequency = str(medicine.get("frequency") or "").strip()
            duration = str(medicine.get("duration") or "").strip()
            instructions = str(
                medicine.get("instructions") or ""
            ).strip()

            if not all([medicine_name, dosage, frequency, duration]):
                return jsonify({
                    "success": False,
                    "error": (
                        "Har medicine ka name, dosage, frequency "
                        "aur duration required hai."
                    )
                }), 400

            clean_medicines.append({
                "medicine_name": medicine_name[:150],
                "dosage": dosage[:100],
                "frequency": frequency[:100],
                "duration": duration[:100],
                "instructions": instructions or None
            })

        # Create prescription
        prescription_result = (
            supabase.table("prescriptions")
            .insert({
                "appointment_id": appointment_id,
                "patient_id": appointment["patient_id"],
                "doctor_id": appointment["doctor_id"],
                "diagnosis": diagnosis or None,
                "notes": notes or None
            })
            .execute()
        )

        if not prescription_result.data:
            raise Exception("Prescription insert failed")

        prescription = prescription_result.data[0]
        prescription_id = prescription["prescription_id"]

        # Add medicines
        for medicine in clean_medicines:
            medicine["prescription_id"] = prescription_id

        supabase.table("prescription_medicines").insert(
            clean_medicines
        ).execute()

        return jsonify({
            "success": True,
            "message": "Prescription successfully created.",
            "prescription_id": prescription_id
        }), 201

    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "error": "Appointment ID valid number hona chahiye."
        }), 400

    except Exception:
        app.logger.exception("Prescription creation failed")
        return jsonify({
            "success": False,
            "error": (
                "Prescription save nahi hui. Database error check karo."
            )
        }), 500


# ==========================================
# PRESCRIPTION MEDICINES API
# ==========================================

@app.route(
    "/prescriptions/<int:prescription_id>/medicines",
    methods=["GET"]
)
def prescription_medicines_api(prescription_id):
    try:
        result = (
            supabase.table("prescription_medicines")
            .select("*")
            .eq("prescription_id", prescription_id)
            .order("medicine_id")
            .execute()
        )

        return jsonify({
            "success": True,
            "medicines": result.data or []
        }), 200

    except Exception:
        app.logger.exception("Prescription medicines load failed")
        return jsonify({
            "success": False,
            "error": "Medicines load nahi ho sakin."
        }), 500

# ==========================================
# PRESCRIPTIONS WEB PAGE
# ==========================================

@app.route("/web/prescriptions", methods=["GET"])
def prescriptions_page():
    appointments = []
    message = None

    try:
        # Load appointments with patient and doctor names
        appointments_result = (
            supabase.table("appointments")
            .select(
                "appointment_id, patient_id, doctor_id, "
                "appointment_date, appointment_time, status, "
                "patients!fk_patient(full_name), "
                "doctors!fk_doctor(full_name, specialization)"
            )
            .order("appointment_date", desc=True)
            .order("appointment_time", desc=True)
            .execute()
        )

        # Find appointments that already have a prescription
        existing_result = (
            supabase.table("prescriptions")
            .select("appointment_id")
            .execute()
        )

        used_appointment_ids = {
            item["appointment_id"]
            for item in (existing_result.data or [])
        }

        # One prescription per appointment
        appointments = [
            item for item in (appointments_result.data or [])
            if item["appointment_id"] not in used_appointment_ids
        ]

    except Exception:
        app.logger.exception("Prescriptions page load failed")
        message = (
            "Appointments load nahi hui. Database connection "
            "aur foreign-key relationships check karo."
        )

    return render_template(
        "prescriptions.html",
        appointments=appointments,
        message=message
    )

# ==========================================
# EDIT PRESCRIPTION API
# ==========================================

@app.route("/prescriptions/<int:prescription_id>", methods=["PUT"])
def edit_prescription_api(prescription_id):
    data = request.get_json(silent=True) or {}

    try:
        existing_result = (
            supabase.table("prescriptions")
            .select("prescription_id")
            .eq("prescription_id", prescription_id)
            .limit(1)
            .execute()
        )

        if not existing_result.data:
            return jsonify({
                "success": False,
                "error": "Prescription nahi mili."
            }), 404

        # Only update fields that were provided
        update_data = {}

        if "diagnosis" in data:
            update_data["diagnosis"] = (
                str(data.get("diagnosis") or "").strip() or None
            )

        if "notes" in data:
            update_data["notes"] = (
                str(data.get("notes") or "").strip() or None
            )

        medicines_provided = "medicines" in data
        clean_medicines = []

        if medicines_provided:
            medicines = data["medicines"]

            if not isinstance(medicines, list) or not medicines:
                return jsonify({
                    "success": False,
                    "error": "Kam se kam ek medicine required hai."
                }), 400

            for medicine in medicines:
                if not isinstance(medicine, dict):
                    return jsonify({
                        "success": False,
                        "error": "Medicine details ka format invalid hai."
                    }), 400

                name = str(medicine.get("medicine_name") or "").strip()
                dosage = str(medicine.get("dosage") or "").strip()
                frequency = str(medicine.get("frequency") or "").strip()
                duration = str(medicine.get("duration") or "").strip()
                instructions = str(
                    medicine.get("instructions") or ""
                ).strip()

                if not all([name, dosage, frequency, duration]):
                    return jsonify({
                        "success": False,
                        "error": (
                            "Medicine name, dosage, frequency aur "
                            "duration required hain."
                        )
                    }), 400

                clean_medicines.append({
                    "prescription_id": prescription_id,
                    "medicine_name": name[:150],
                    "dosage": dosage[:100],
                    "frequency": frequency[:100],
                    "duration": duration[:100],
                    "instructions": instructions or None
                })

        if update_data:
            (
                supabase.table("prescriptions")
                .update(update_data)
                .eq("prescription_id", prescription_id)
                .execute()
            )

        # If medicines were supplied, replace the medicine list
        if medicines_provided:
            (
                supabase.table("prescription_medicines")
                .delete()
                .eq("prescription_id", prescription_id)
                .execute()
            )

            (
                supabase.table("prescription_medicines")
                .insert(clean_medicines)
                .execute()
            )

        return jsonify({
            "success": True,
            "message": "Prescription successfully updated."
        }), 200

    except Exception:
        app.logger.exception("Prescription update failed")
        return jsonify({
            "success": False,
            "error": "Prescription update nahi hui. Terminal error check karo."
        }), 500


# ==========================================
# DELETE PRESCRIPTION API
# ==========================================

@app.route(
    "/prescriptions/<int:prescription_id>",
    methods=["DELETE"]
)
def delete_prescription_api(prescription_id):
    try:
        existing_result = (
            supabase.table("prescriptions")
            .select("prescription_id")
            .eq("prescription_id", prescription_id)
            .limit(1)
            .execute()
        )

        if not existing_result.data:
            return jsonify({
                "success": False,
                "error": "Prescription nahi mili."
            }), 404

        (
            supabase.table("prescriptions")
            .delete()
            .eq("prescription_id", prescription_id)
            .execute()
        )

        # Database ON DELETE CASCADE removes linked medicines
        return jsonify({
            "success": True,
            "message": "Prescription successfully deleted."
        }), 200

    except Exception:
        app.logger.exception("Prescription deletion failed")
        return jsonify({
            "success": False,
            "error": "Prescription delete nahi hui. Terminal error check karo."
        }), 500

if __name__ == "__main__":
    app.run(debug=True)
