"""Seed database with scenario-specific mock data for CEO demo."""

from datetime import date, time, timedelta
from app.db.database import SessionLocal, init_db
from app.db.models import (
    Employee, LeaveBalance, LeaveRequest, Payslip, Excuse, Ticket,
    LeaveType, RequestStatus, ExcuseType
)


def get_next_monday() -> date:
    """Get the next Monday from today."""
    today = date.today()
    days_ahead = 7 - today.weekday()  # Monday is 0
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


def seed_database(force: bool = False):
    """
    Populate database with SCENARIO-SPECIFIC mock data.
    
    Key Scenarios:
    1. Conflict Detection: Khalid (EMP002) has approved leave on next Monday
       → When Ahmed tries to book same day, AI should warn about team conflict
    2. Insufficient Balance: Omar (EMP005) has only 2 days annual leave
    3. Eligibility Check: Omar hired < 1 year → Cannot request salary advance
    
    Args:
        force: If True, skip the check and force reseeding even if data exists.
    """
    
    # Initialize tables
    init_db()
    
    db = SessionLocal()
    
    try:
        # Check if already seeded (unless forcing)
        if not force and db.query(Employee).first():
            print("✅ Database already seeded. Skipping...")
            return
        
        # ============================================
        # EMPLOYEES - Scenario-Driven Team Structure
        # ============================================
        employees = [
            # THE APPLICANT - Main demo user
            Employee(
                id="EMP001",
                name="Ahmed Al-Rashid",
                name_ar="أحمد الراشد",
                email="ahmed.rashid@company.com",
                department="Engineering",
                title="Senior Developer",
                hire_date=date(2021, 3, 15)  # 3+ years → Eligible for salary advance
            ),
            # THE COLLEAGUE - Same team, has leave conflict
            Employee(
                id="EMP002",
                name="Khalid Ibrahim",
                name_ar="خالد إبراهيم",
                email="khalid.ibrahim@company.com",
                department="Engineering",  # ⭐ SAME DEPARTMENT as Ahmed
                title="Software Developer",
                hire_date=date(2022, 6, 1)
            ),
            # THE MANAGER
            Employee(
                id="EMP003",
                name="Sara Mohammed",
                name_ar="سارة محمد",
                email="sara.mohammed@company.com",
                department="Engineering",  # ⭐ Manager of Engineering
                title="Engineering Manager",
                hire_date=date(2019, 1, 10)
            ),
            # HR PERSON - For testing HR-specific queries
            Employee(
                id="EMP004",
                name="Fatima Hassan",
                name_ar="فاطمة حسن",
                email="fatima.hassan@company.com",
                department="HR",
                title="HR Specialist",
                hire_date=date(2020, 9, 20)
            ),
            # NEW EMPLOYEE - < 1 year, low balance
            Employee(
                id="EMP005",
                name="Omar Nasser",
                name_ar="عمر ناصر",
                email="omar.nasser@company.com",
                department="Engineering",
                title="Junior Developer",
                hire_date=date(2024, 8, 5)  # ⭐ Less than 1 year → Cannot request salary advance
            ),
        ]
        db.add_all(employees)
        db.flush()
        
        print("✅ Created 5 employees with team structure")
        
        # ============================================
        # LEAVE BALANCES
        # ============================================
        leave_balances = [
            # Ahmed - Normal balances
            LeaveBalance(employee_id="EMP001", leave_type=LeaveType.ANNUAL, balance_days=21),
            LeaveBalance(employee_id="EMP001", leave_type=LeaveType.SICK, balance_days=10),
            LeaveBalance(employee_id="EMP001", leave_type=LeaveType.UNPAID, balance_days=30),
            
            # Khalid - Normal balances
            LeaveBalance(employee_id="EMP002", leave_type=LeaveType.ANNUAL, balance_days=18),
            LeaveBalance(employee_id="EMP002", leave_type=LeaveType.SICK, balance_days=8),
            LeaveBalance(employee_id="EMP002", leave_type=LeaveType.UNPAID, balance_days=30),
            
            # Sara (Manager) - Normal balances
            LeaveBalance(employee_id="EMP003", leave_type=LeaveType.ANNUAL, balance_days=25),
            LeaveBalance(employee_id="EMP003", leave_type=LeaveType.SICK, balance_days=10),
            LeaveBalance(employee_id="EMP003", leave_type=LeaveType.UNPAID, balance_days=30),
            
            # Fatima (HR) - Normal balances
            LeaveBalance(employee_id="EMP004", leave_type=LeaveType.ANNUAL, balance_days=21),
            LeaveBalance(employee_id="EMP004", leave_type=LeaveType.SICK, balance_days=10),
            LeaveBalance(employee_id="EMP004", leave_type=LeaveType.UNPAID, balance_days=30),
            
            # Omar (New) - ⭐ LOW BALANCE for testing insufficient balance scenario
            LeaveBalance(employee_id="EMP005", leave_type=LeaveType.ANNUAL, balance_days=2),
            LeaveBalance(employee_id="EMP005", leave_type=LeaveType.SICK, balance_days=3),
            LeaveBalance(employee_id="EMP005", leave_type=LeaveType.UNPAID, balance_days=30),
        ]
        db.add_all(leave_balances)
        
        print("✅ Created leave balances (Omar has only 2 days annual)")
        
        # ============================================
        # ⭐ CRITICAL: KHALID'S APPROVED LEAVES (Conflict Scenario)
        # ============================================
        next_monday = get_next_monday()

        conflict_leave = LeaveRequest(
            employee_id="EMP002",  # Khalid
            leave_type=LeaveType.ANNUAL,
            start_date=next_monday,
            end_date=next_monday,
            reason="Family commitment",
            status=RequestStatus.APPROVED  # ⭐ Already approved!
        )
        db.add(conflict_leave)

        # Additional fixed conflict for testing - January 26, 2026
        fixed_conflict = LeaveRequest(
            employee_id="EMP002",  # Khalid
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 1, 26),
            end_date=date(2026, 1, 26),
            reason="Personal appointment",
            status=RequestStatus.APPROVED
        )
        db.add(fixed_conflict)

        print(f"✅ Created Khalid's approved leave on {next_monday} (next Monday)")
        print(f"✅ Created Khalid's approved leave on 2026-01-26 (fixed test date)")
        
        # ============================================
        # PAYSLIPS - Last 3 months
        # ============================================
        salary_data = {
            "EMP001": {"basic": 15000, "housing": 3000, "transport": 500, "other": 1000, "deductions": 1500},
            "EMP002": {"basic": 12000, "housing": 2500, "transport": 500, "other": 800, "deductions": 1200},
            "EMP003": {"basic": 20000, "housing": 4000, "transport": 500, "other": 2000, "deductions": 2000},
            "EMP004": {"basic": 11000, "housing": 2200, "transport": 500, "other": 600, "deductions": 1100},
            "EMP005": {"basic": 7000, "housing": 1500, "transport": 500, "other": 300, "deductions": 700},
        }
        
        payslips = []
        for emp_id, data in salary_data.items():
            for month_offset in range(3):  # Current, last month, 2 months ago
                current_month = date.today().month - month_offset
                current_year = date.today().year
                if current_month <= 0:
                    current_month += 12
                    current_year -= 1
                
                net = data["basic"] + data["housing"] + data["transport"] + data["other"] - data["deductions"]
                payslips.append(Payslip(
                    employee_id=emp_id,
                    month=current_month,
                    year=current_year,
                    net_salary=net,
                    basic_salary=data["basic"],
                    housing_allowance=data["housing"],
                    transport_allowance=data["transport"],
                    other_allowances=data["other"],
                    deductions=data["deductions"]
                ))
        
        db.add_all(payslips)
        print("✅ Created 15 payslips (3 months × 5 employees)")
        
        # ============================================
        # SAMPLE TICKET - For status check testing
        # ============================================
        sample_ticket = Ticket(
            employee_id="EMP001",  # Ahmed's pending ticket
            category="IT",
            description="VPN connection issues when working remotely",
            status=RequestStatus.PENDING
        )
        db.add(sample_ticket)
        
        print("✅ Created sample support ticket for Ahmed")
        
        db.commit()
        
        print("\n" + "="*50)
        print("🎉 DATABASE SEEDED SUCCESSFULLY!")
        print("="*50)
        print("\n📋 Demo Scenarios Ready:")
        print(f"   1. Conflict: Ahmed asks for leave on {next_monday} → Khalid already approved")
        print("   2. Low Balance: Omar (EMP005) has only 2 days annual leave")
        print("   3. Salary Advance: Omar < 1 year tenure → Not eligible")
        print("\n👤 Demo User: Ahmed (EMP001) - ahmed.rashid@company.com")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
