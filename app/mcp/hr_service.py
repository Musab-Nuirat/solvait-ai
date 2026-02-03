"""HR Service Layer - Business logic for HR operations."""

from datetime import date, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import io

from app.db.models import (
    Employee, LeaveBalance, LeaveRequest, Payslip, Excuse, Ticket,
    LeaveType, RequestStatus, ExcuseType
)
from app.config import API_BASE_URL


class HRService:
    """Business logic layer for HR operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ============================================
    # READ OPERATIONS
    # ============================================
    
    def get_employee_profile(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Get employee profile information."""
        employee = self.db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            return None
        
        tenure_days = (date.today() - employee.hire_date).days
        tenure_years = tenure_days / 365
        
        return {
            "id": employee.id,
            "name": employee.name,
            "name_ar": employee.name_ar,
            "email": employee.email,
            "department": employee.department,
            "title": employee.title,
            "hire_date": employee.hire_date.isoformat(),
            "tenure_years": round(tenure_years, 1),
            "eligible_for_advance": tenure_years >= 1  # ⭐ Salary advance eligibility
        }
    
    def get_leave_balance(
        self, 
        employee_id: str, 
        leave_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get leave balance for an employee."""
        query = self.db.query(LeaveBalance).filter(LeaveBalance.employee_id == employee_id)
        
        if leave_type:
            try:
                lt = LeaveType(leave_type.lower())
                query = query.filter(LeaveBalance.leave_type == lt)
            except ValueError:
                return {"error": f"Invalid leave type: {leave_type}"}
        
        balances = query.all()
        
        if not balances:
            return {"error": f"No leave balance found for employee {employee_id}"}
        
        return {
            "employee_id": employee_id,
            "balances": [
                {
                    "type": b.leave_type.value,
                    "type_ar": self._get_leave_type_arabic(b.leave_type),
                    "remaining_days": b.balance_days
                }
                for b in balances
            ]
        }
    
    def get_team_members(self, department: str) -> Dict[str, Any]:
        """
        Get all team members in a department.
        Useful for knowing who's on your team before checking calendars.
        """
        employees = self.db.query(Employee).filter(
            Employee.department == department
        ).all()

        if not employees:
            return {"error": f"No employees found in department: {department}"}

        return {
            "department": department,
            "team_size": len(employees),
            "members": [
                {
                    "id": e.id,
                    "name": e.name,
                    "name_ar": e.name_ar,
                    "title": e.title
                }
                for e in employees
            ]
        }

    def get_team_calendar(
        self,
        department: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Get team leave calendar to detect conflicts.
        Returns all approved/pending leave requests for a department in date range.
        """
        # Get all employees in the department
        dept_employees = self.db.query(Employee).filter(
            Employee.department == department
        ).all()
        
        employee_ids = [e.id for e in dept_employees]
        
        # Get leave requests that overlap with the date range
        leaves = self.db.query(LeaveRequest).filter(
            LeaveRequest.employee_id.in_(employee_ids),
            LeaveRequest.status.in_([RequestStatus.APPROVED, RequestStatus.PENDING]),
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date
        ).all()
        
        conflicts = []
        for leave in leaves:
            emp = next((e for e in dept_employees if e.id == leave.employee_id), None)
            conflicts.append({
                "employee_id": leave.employee_id,
                "employee_name": emp.name if emp else "Unknown",
                "employee_name_ar": emp.name_ar if emp else "غير معروف",
                "leave_type": leave.leave_type.value,
                "start_date": leave.start_date.isoformat(),
                "end_date": leave.end_date.isoformat(),
                "status": leave.status.value
            })
        
        return {
            "department": department,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "team_leaves": conflicts,
            "has_conflicts": len(conflicts) > 0
        }
    
    def get_payslip(
        self,
        employee_id: str,
        month: Optional[int] = None,
        year: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get payslip for an employee with full breakdown."""
        query = self.db.query(Payslip).filter(Payslip.employee_id == employee_id)

        if month and year:
            query = query.filter(Payslip.month == month, Payslip.year == year)
        else:
            # Get latest payslip
            query = query.order_by(Payslip.year.desc(), Payslip.month.desc())

        payslip = query.first()

        if not payslip:
            return {"error": f"No payslip found for employee {employee_id}"}

        # Get month name for display
        month_names = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December"
        }
        month_names_ar = {
            1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل",
            5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس",
            9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
        }

        # Calculate totals
        total_allowances = (
            (payslip.housing_allowance or 0) +
            (payslip.transport_allowance or 0) +
            (payslip.phone_allowance or 0) +
            (payslip.meal_allowance or 0) +
            (payslip.other_allowances or 0)
        )

        total_deductions = (
            (payslip.gosi_deduction or 0) +
            (payslip.tax_deduction or 0) +
            (payslip.loan_deduction or 0) +
            (payslip.absence_deduction or 0) +
            (payslip.other_deductions or 0)
        )

        return {
            "employee_id": employee_id,
            "period": f"{payslip.year}-{str(payslip.month).zfill(2)}",
            "period_display": f"{month_names.get(payslip.month, payslip.month)} {payslip.year}",
            "period_display_ar": f"{month_names_ar.get(payslip.month, payslip.month)} {payslip.year}",
            "net_salary": payslip.net_salary,
            "basic_salary": payslip.basic_salary,
            "allowances": {
                "housing_allowance": payslip.housing_allowance or 0,
                "housing_allowance_ar": "بدل سكن",
                "transport_allowance": payslip.transport_allowance or 0,
                "transport_allowance_ar": "بدل مواصلات",
                "phone_allowance": payslip.phone_allowance or 0,
                "phone_allowance_ar": "بدل هاتف",
                "meal_allowance": payslip.meal_allowance or 0,
                "meal_allowance_ar": "بدل طعام",
                "other_allowances": payslip.other_allowances or 0,
                "other_allowances_ar": "بدلات أخرى",
                "total": total_allowances,
                "total_ar": "إجمالي البدلات"
            },
            "deductions": {
                "gosi_deduction": payslip.gosi_deduction or 0,
                "gosi_deduction_ar": "التأمينات الاجتماعية (GOSI)",
                "tax_deduction": payslip.tax_deduction or 0,
                "tax_deduction_ar": "ضريبة الدخل",
                "loan_deduction": payslip.loan_deduction or 0,
                "loan_deduction_ar": "قسط القرض",
                "absence_deduction": payslip.absence_deduction or 0,
                "absence_deduction_ar": "خصم الغياب",
                "other_deductions": payslip.other_deductions or 0,
                "other_deductions_ar": "استقطاعات أخرى",
                "total": total_deductions,
                "total_ar": "إجمالي الاستقطاعات"
            },
            "download_available": True,
            "download_url": f"{API_BASE_URL}/payslip/download/{employee_id}/{payslip.year}/{payslip.month}"
        }

    def generate_payslip_pdf(
        self,
        employee_id: str,
        month: Optional[int] = None,
        year: Optional[int] = None
    ) -> Optional[bytes]:
        """Generate a PDF payslip for download."""
        from fpdf import FPDF

        # Get payslip data
        payslip_data = self.get_payslip(employee_id, month, year)
        if "error" in payslip_data:
            return None

        # Get employee info
        employee = self.db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            return None

        # Create PDF
        pdf = FPDF()
        pdf.add_page()

        # Title
        pdf.set_font("Helvetica", "B", 20)
        pdf.cell(0, 15, "PAYSLIP", ln=True, align="C")
        pdf.ln(5)

        # Company name
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 8, "Solvait Company", ln=True, align="C")
        pdf.ln(10)

        # Period
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, f"Period: {payslip_data.get('period_display', '')}", ln=True, align="C")
        pdf.ln(10)

        # Employee info
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, f"Employee ID: {employee_id}", ln=True)
        pdf.cell(0, 8, f"Name: {employee.name}", ln=True)
        pdf.cell(0, 8, f"Department: {employee.department}", ln=True)
        pdf.ln(10)

        # Earnings section
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(0, 8, "EARNINGS", ln=True, fill=True)
        pdf.set_font("Helvetica", "", 11)

        basic = payslip_data.get("basic_salary", 0)
        allowances = payslip_data.get("allowances", {})

        pdf.cell(120, 7, "Basic Salary", border=0)
        pdf.cell(0, 7, f"SAR {basic:,.2f}", ln=True, align="R")

        pdf.cell(120, 7, "Housing Allowance", border=0)
        pdf.cell(0, 7, f"SAR {allowances.get('housing_allowance', 0):,.2f}", ln=True, align="R")

        pdf.cell(120, 7, "Transport Allowance", border=0)
        pdf.cell(0, 7, f"SAR {allowances.get('transport_allowance', 0):,.2f}", ln=True, align="R")

        pdf.cell(120, 7, "Phone Allowance", border=0)
        pdf.cell(0, 7, f"SAR {allowances.get('phone_allowance', 0):,.2f}", ln=True, align="R")

        pdf.cell(120, 7, "Meal Allowance", border=0)
        pdf.cell(0, 7, f"SAR {allowances.get('meal_allowance', 0):,.2f}", ln=True, align="R")

        pdf.cell(120, 7, "Other Allowances", border=0)
        pdf.cell(0, 7, f"SAR {allowances.get('other_allowances', 0):,.2f}", ln=True, align="R")

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(120, 7, "Total Earnings", border="T")
        gross = basic + allowances.get("total", 0)
        pdf.cell(0, 7, f"SAR {gross:,.2f}", ln=True, align="R", border="T")
        pdf.ln(5)

        # Deductions section
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "DEDUCTIONS", ln=True, fill=True)
        pdf.set_font("Helvetica", "", 11)

        deductions = payslip_data.get("deductions", {})

        pdf.cell(120, 7, "GOSI (Social Insurance)", border=0)
        pdf.cell(0, 7, f"SAR {deductions.get('gosi_deduction', 0):,.2f}", ln=True, align="R")

        pdf.cell(120, 7, "Tax", border=0)
        pdf.cell(0, 7, f"SAR {deductions.get('tax_deduction', 0):,.2f}", ln=True, align="R")

        pdf.cell(120, 7, "Loan Repayment", border=0)
        pdf.cell(0, 7, f"SAR {deductions.get('loan_deduction', 0):,.2f}", ln=True, align="R")

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(120, 7, "Total Deductions", border="T")
        pdf.cell(0, 7, f"SAR {deductions.get('total', 0):,.2f}", ln=True, align="R", border="T")
        pdf.ln(10)

        # Net Salary
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_fill_color(200, 230, 200)
        pdf.cell(120, 10, "NET SALARY", fill=True)
        pdf.cell(0, 10, f"SAR {payslip_data.get('net_salary', 0):,.2f}", ln=True, align="R", fill=True)
        pdf.ln(15)

        # Footer
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, "This is a computer-generated document.", ln=True, align="C")
        pdf.cell(0, 6, f"Generated on: {date.today().strftime('%Y-%m-%d')}", ln=True, align="C")

        # Return PDF bytes
        return pdf.output()

    def get_ticket_status(self, ticket_id: int) -> Dict[str, Any]:
        """Get status of a support ticket."""
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        
        if not ticket:
            return {"error": f"Ticket #{ticket_id} not found"}
        
        return {
            "ticket_id": ticket.id,
            "category": ticket.category,
            "description": ticket.description,
            "status": ticket.status.value,
            "status_ar": self._get_status_arabic(ticket.status),
            "created_at": ticket.created_at.isoformat()
        }
    
    # ============================================
    # WRITE OPERATIONS
    # ============================================
    
    def submit_leave_request(
        self,
        employee_id: str,
        leave_type: str,
        start_date: date,
        end_date: date,
        reason: Optional[str] = None,
        confirm_conflicts: bool = False
    ) -> Dict[str, Any]:
        """
        Submit a new leave request with validation.

        IMPORTANT: If team conflicts exist and confirm_conflicts=False,
        this will return a warning instead of submitting. The agent must
        inform the user about conflicts and get confirmation before
        calling again with confirm_conflicts=True.
        """

        # 1. Validate leave type - map synonyms
        leave_type_mapping = {
            "annual": "annual",
            "sick": "sick",
            "unpaid": "unpaid",
            "medical": "sick",  # Map medical to sick
            "مرضية": "sick",    # Arabic medical
            "سنوية": "annual",  # Arabic annual
            "بدون راتب": "unpaid",  # Arabic unpaid
        }
        normalized_type = leave_type_mapping.get(leave_type.lower(), leave_type.lower())

        try:
            lt = LeaveType(normalized_type)
        except ValueError:
            return {"error": f"Invalid leave type: {leave_type}. Use: annual, sick/medical, or unpaid"}

        # 1.5 Validate dates
        if end_date < start_date:
            return {"error": "Invalid date range: End date cannot be before start date."}

        # 2. Calculate requested days
        requested_days = (end_date - start_date).days + 1

        # 3. Check balance (skip for unpaid)
        balance = None
        if lt != LeaveType.UNPAID:
            balance = self.db.query(LeaveBalance).filter(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.leave_type == lt
            ).first()

            if not balance or balance.balance_days < requested_days:
                available = balance.balance_days if balance else 0
                return {
                    "error": "insufficient_balance",
                    "message": f"Insufficient {leave_type} leave balance. You have {available} days but requested {requested_days} days.",
                    "message_ar": f"رصيد الإجازات غير كافٍ. لديك {available} يوم ولكنك طلبت {requested_days} يوم.",
                    "suggestion": "You may request Unpaid Leave instead."
                }

        # 4. Check for team conflicts (if not already confirmed)
        if not confirm_conflicts:
            # Get employee's department
            employee = self.db.query(Employee).filter(Employee.id == employee_id).first()
            if employee:
                conflicts = self.get_team_calendar(employee.department, start_date, end_date)
                # Filter out the current employee from conflicts
                team_conflicts = [
                    c for c in conflicts.get("team_leaves", [])
                    if c["employee_id"] != employee_id
                ]

                if team_conflicts:
                    conflict_names = [f"{c['employee_name']} ({c['start_date']} to {c['end_date']})" for c in team_conflicts]
                    conflict_names_ar = [f"{c['employee_name_ar']} (من {c['start_date']} إلى {c['end_date']})" for c in team_conflicts]

                    return {
                        "warning": "team_conflict",
                        "message": f"Team conflict detected! The following colleagues have leave during this period: {', '.join(conflict_names)}. Please confirm with the user if they want to proceed anyway.",
                        "message_ar": f"تم اكتشاف تعارض مع الفريق! الزملاء التاليون لديهم إجازة في هذه الفترة: {', '.join(conflict_names_ar)}. يرجى التأكد من المستخدم إذا كان يريد المتابعة.",
                        "conflicts": team_conflicts,
                        "action_required": "Ask user to confirm if they want to proceed despite the conflict. If yes, call submit_leave_request again with confirm_conflicts=True"
                    }

        # 5. Create leave request with strict balance validation (no conflicts or user confirmed)
        # Re-fetch and lock the balance to prevent race conditions
        remaining_balance = None
        original_balance = None

        if lt != LeaveType.UNPAID:
            # Re-query balance with lock to ensure atomicity
            balance = self.db.query(LeaveBalance).filter(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.leave_type == lt
            ).with_for_update().first()

            if not balance:
                return {
                    "error": "balance_not_found",
                    "message": f"No {leave_type} leave balance found for employee {employee_id}.",
                    "message_ar": f"لم يتم العثور على رصيد إجازة {self._get_leave_type_arabic(lt)} للموظف."
                }

            # STRICT VALIDATION: Re-check balance before deducting
            if balance.balance_days < requested_days:
                return {
                    "error": "insufficient_balance",
                    "message": f"Insufficient balance. You have {balance.balance_days} days but requested {requested_days}.",
                    "message_ar": f"رصيد غير كافٍ. لديك {balance.balance_days} يوم ولكنك طلبت {requested_days} يوم."
                }

            original_balance = balance.balance_days

            # Deduct immediately while lock is held
            balance.balance_days -= requested_days
            remaining_balance = balance.balance_days

            # CRITICAL: Prevent negative balances (should never happen but extra safety)
            if remaining_balance < 0:
                self.db.rollback()
                return {
                    "error": "balance_underflow",
                    "message": "Cannot process request - would result in negative balance.",
                    "message_ar": "لا يمكن معالجة الطلب - سيؤدي إلى رصيد سالب."
                }

        # Create the leave request
        leave_request = LeaveRequest(
            employee_id=employee_id,
            leave_type=lt,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            status=RequestStatus.PENDING
        )
        self.db.add(leave_request)
        self.db.flush()  # Get the ID

        self.db.commit()

        # Build response with balance info
        result = {
            "success": True,
            "request_id": f"LR-{leave_request.id:04d}",
            "message": f"Leave request submitted successfully for {start_date} to {end_date}",
            "message_ar": f"تم تقديم طلب الإجازة بنجاح للفترة من {start_date} إلى {end_date}",
            "details": {
                "type": leave_type,
                "days": requested_days,
                "status": "pending"
            }
        }

        # Add balance info if applicable
        if remaining_balance is not None:
            result["balance_info"] = {
                "original": original_balance,
                "used": requested_days,
                "remaining": remaining_balance
            }
            result["message"] += f". Your {leave_type} leave balance is now {remaining_balance} days."
            result["message_ar"] += f". رصيد إجازتك {self._get_leave_type_arabic(lt)} الآن {remaining_balance} يوم."

        return result
    
    def check_duplicate_excuse(
        self,
        employee_id: str,
        excuse_date: date,
        excuse_type: str
    ) -> Dict[str, Any]:
        """Check if a similar excuse already exists for the same date and type."""
        try:
            et = ExcuseType(excuse_type.lower())
        except ValueError:
            return {"exists": False}

        existing = self.db.query(Excuse).filter(
            Excuse.employee_id == employee_id,
            Excuse.date == excuse_date,
            Excuse.excuse_type == et
        ).first()

        if existing:
            return {
                "exists": True,
                "excuse_id": f"EX-{existing.id:04d}",
                "date": excuse_date.isoformat(),
                "type": excuse_type,
                "reason": existing.reason,
                "status": existing.status.value
            }
        return {"exists": False}

    def create_excuse(
        self,
        employee_id: str,
        excuse_date: date,
        excuse_type: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        reason: str = ""
    ) -> Dict[str, Any]:
        """Create an excuse request for late arrival or early departure."""

        # Check for duplicate excuse first
        duplicate_check = self.check_duplicate_excuse(employee_id, excuse_date, excuse_type)
        if duplicate_check.get("exists"):
            return {
                "error": "duplicate_excuse",
                "message": f"An excuse for {excuse_type.replace('_', ' ')} on {excuse_date} already exists (ID: {duplicate_check['excuse_id']}). Status: {duplicate_check['status']}.",
                "message_ar": f"يوجد استئذان مسجل مسبقاً لنفس اليوم والنوع (رقم: {duplicate_check['excuse_id']}). الحالة: {duplicate_check['status']}.",
                "existing_excuse": duplicate_check
            }

        # Validate reason is provided
        if not reason or not reason.strip():
            return {"error": "Reason is required for excuse requests"}
        
        # Validate excuse type
        try:
            et = ExcuseType(excuse_type.lower())
        except ValueError:
            return {"error": f"Invalid excuse type: {excuse_type}. Use: late_arrival or early_departure"}
        
        # Parse times with error handling - supports various formats
        from datetime import datetime
        import re
        st = None
        et_time = None

        def parse_time(time_str: str) -> tuple:
            """Parse time string in various formats and return (hour, minute) tuple.

            Supported formats:
            - "8:17", "08:17" (24-hour)
            - "8.17", "08.17" (with dot separator)
            - "8:30 AM", "8:30 am", "8:30AM" (12-hour with AM/PM)
            - "3:00 PM", "3:00 pm", "3:00PM" (12-hour with AM/PM)
            - "8am", "3pm" (hour only with AM/PM)
            """
            if not time_str:
                return None

            # Remove any extra whitespace and convert to lowercase for easier parsing
            time_str = time_str.strip()
            time_lower = time_str.lower()

            # Check for AM/PM format
            is_pm = 'pm' in time_lower or 'p.m' in time_lower
            is_am = 'am' in time_lower or 'a.m' in time_lower

            # Remove AM/PM suffixes for parsing
            clean_time = re.sub(r'\s*(am|pm|a\.m\.?|p\.m\.?)\s*', '', time_lower, flags=re.IGNORECASE).strip()

            # Handle hour-only format like "8am" or "3pm"
            if clean_time.isdigit():
                hour = int(clean_time)
                minute = 0
            else:
                # Handle formats like "8:17", "08:17", "8.17", "08.17"
                if ':' in clean_time:
                    parts = clean_time.split(':')
                elif '.' in clean_time:
                    parts = clean_time.split('.')
                else:
                    return None

                if len(parts) != 2:
                    return None

                try:
                    hour = int(parts[0])
                    minute = int(parts[1])
                except ValueError:
                    return None

            # Convert 12-hour to 24-hour format
            if is_pm and hour < 12:
                hour += 12
            elif is_am and hour == 12:
                hour = 0

            # Validate ranges
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                return None

            return (hour, minute)
        
        if start_time:
            parsed = parse_time(start_time)
            if parsed is None:
                return {"error": f"Invalid start_time format: {start_time}. Use HH:MM format (e.g., 8:17 or 08:17)"}
            hour, minute = parsed
            st = datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
        
        if end_time:
            parsed = parse_time(end_time)
            if parsed is None:
                return {"error": f"Invalid end_time format: {end_time}. Use HH:MM format (e.g., 15:00 or 8:17)"}
            hour, minute = parsed
            et_time = datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
        
        try:
            excuse = Excuse(
                employee_id=employee_id,
                date=excuse_date,
                excuse_type=et,
                start_time=st,
                end_time=et_time,
                reason=reason.strip(),
                status=RequestStatus.PENDING
            )
            self.db.add(excuse)
            self.db.flush()  # Get the ID before commit
            self.db.commit()
            
            return {
                "success": True,
                "excuse_id": f"EX-{excuse.id:04d}",
                "message": f"Excuse request submitted for {excuse_date}",
                "message_ar": f"تم تسجيل طلب الاستئذان بنجاح. رقم الطلب EX-{excuse.id:04d}.",
                "details": {
                    "type": excuse_type,
                    "date": excuse_date.isoformat(),
                    "status": "pending"
                }
            }
        except Exception as e:
            self.db.rollback()
            return {"error": f"Failed to create excuse: {str(e)}"}
    
    def create_support_ticket(
        self,
        employee_id: str,
        category: str,
        description: str
    ) -> Dict[str, Any]:
        """Create a new support ticket."""
        
        ticket = Ticket(
            employee_id=employee_id,
            category=category,
            description=description,
            status=RequestStatus.PENDING
        )
        self.db.add(ticket)
        self.db.commit()
        
        return {
            "success": True,
            "ticket_id": f"TK-{ticket.id:04d}",
            "message": f"Support ticket created successfully",
            "details": {
                "category": category,
                "status": "pending"
            }
        }
    
    # ============================================
    # HELPER METHODS
    # ============================================
    
    def _get_leave_type_arabic(self, leave_type: LeaveType) -> str:
        """Get Arabic translation for leave type."""
        translations = {
            LeaveType.ANNUAL: "إجازة سنوية",
            LeaveType.SICK: "إجازة مرضية",
            LeaveType.UNPAID: "إجازة بدون راتب"
        }
        return translations.get(leave_type, leave_type.value)
    
    def _get_status_arabic(self, status: RequestStatus) -> str:
        """Get Arabic translation for status."""
        translations = {
            RequestStatus.PENDING: "قيد الانتظار",
            RequestStatus.APPROVED: "موافق عليه",
            RequestStatus.REJECTED: "مرفوض",
            RequestStatus.RESOLVED: "تم الحل"
        }
        return translations.get(status, status.value)
