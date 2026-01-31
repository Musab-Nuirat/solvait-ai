"""HR Service Layer - Business logic for HR operations."""

from datetime import date, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import (
    Employee, LeaveBalance, LeaveRequest, Payslip, Excuse, Ticket,
    LeaveType, RequestStatus, ExcuseType
)


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
        """Get payslip for an employee."""
        query = self.db.query(Payslip).filter(Payslip.employee_id == employee_id)
        
        if month and year:
            query = query.filter(Payslip.month == month, Payslip.year == year)
        else:
            # Get latest payslip
            query = query.order_by(Payslip.year.desc(), Payslip.month.desc())
        
        payslip = query.first()
        
        if not payslip:
            return {"error": f"No payslip found for employee {employee_id}"}
        
        return {
            "employee_id": employee_id,
            "period": f"{payslip.year}-{str(payslip.month).zfill(2)}",
            "net_salary": payslip.net_salary,
            "breakdown": {
                "basic_salary": payslip.basic_salary,
                "housing_allowance": payslip.housing_allowance,
                "transport_allowance": payslip.transport_allowance,
                "other_allowances": payslip.other_allowances,
                "total_allowances": payslip.housing_allowance + payslip.transport_allowance + payslip.other_allowances,
                "deductions": payslip.deductions
            }
        }
    
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

        # 1. Validate leave type
        try:
            lt = LeaveType(leave_type.lower())
        except ValueError:
            return {"error": f"Invalid leave type: {leave_type}. Use: annual, sick, or unpaid"}

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

        # 5. Create leave request (no conflicts or user confirmed)
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

        # 6. Deduct from balance (for non-unpaid)
        if lt != LeaveType.UNPAID and balance:
            balance.balance_days -= requested_days

        self.db.commit()

        return {
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
        
        # Parse times with error handling - supports both "8:17" and "08:17" formats
        from datetime import datetime
        st = None
        et_time = None
        
        def parse_time(time_str: str) -> tuple:
            """Parse time string in various formats and return (hour, minute) tuple."""
            if not time_str:
                return None
            
            # Remove any whitespace
            time_str = time_str.strip()
            
            # Handle formats like "8:17", "08:17", "8.17", "08.17"
            if ':' in time_str:
                parts = time_str.split(':')
            elif '.' in time_str:
                parts = time_str.split('.')
            else:
                return None
            
            if len(parts) != 2:
                return None
            
            try:
                hour = int(parts[0])
                minute = int(parts[1])
                
                # Validate ranges
                if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                    return None
                
                return (hour, minute)
            except ValueError:
                return None
        
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
