"""SQLAlchemy database models for Solvait HR system."""

from datetime import date, datetime, time
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Time,
    ForeignKey, Enum, Text, create_engine
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class LeaveType(PyEnum):
    """Types of leave available to employees."""
    ANNUAL = "annual"
    SICK = "sick"
    UNPAID = "unpaid"


class RequestStatus(PyEnum):
    """Status of requests (leave, excuse, ticket)."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESOLVED = "resolved"


class ExcuseType(PyEnum):
    """Types of excuse requests."""
    LATE_ARRIVAL = "late_arrival"
    EARLY_DEPARTURE = "early_departure"


class Employee(Base):
    """Employee master data."""
    __tablename__ = "employees"

    id = Column(String(10), primary_key=True)  # e.g., "EMP001"
    name = Column(String(100), nullable=False)
    name_ar = Column(String(100), nullable=True)  # Arabic name
    email = Column(String(100), unique=True, nullable=False)
    department = Column(String(50), nullable=False)
    title = Column(String(100), nullable=False)
    hire_date = Column(Date, nullable=False)

    # Relationships
    leave_balances = relationship("LeaveBalance", back_populates="employee")
    leave_requests = relationship("LeaveRequest", back_populates="employee")
    payslips = relationship("Payslip", back_populates="employee")
    excuses = relationship("Excuse", back_populates="employee")
    tickets = relationship("Ticket", back_populates="employee")


class LeaveBalance(Base):
    """Current leave balance for each employee by type."""
    __tablename__ = "leave_balances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String(10), ForeignKey("employees.id"), nullable=False)
    leave_type = Column(Enum(LeaveType), nullable=False)
    balance_days = Column(Float, default=0)

    employee = relationship("Employee", back_populates="leave_balances")


class LeaveRequest(Base):
    """Leave requests submitted by employees."""
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String(10), ForeignKey("employees.id"), nullable=False)
    leave_type = Column(Enum(LeaveType), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="leave_requests")


class Payslip(Base):
    """Monthly payslip records."""
    __tablename__ = "payslips"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String(10), ForeignKey("employees.id"), nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    year = Column(Integer, nullable=False)

    # Base salary
    basic_salary = Column(Float, nullable=False)

    # Allowances breakdown
    housing_allowance = Column(Float, default=0)
    transport_allowance = Column(Float, default=0)
    phone_allowance = Column(Float, default=0)       # NEW: Mobile/phone allowance
    meal_allowance = Column(Float, default=0)        # NEW: Food/meal allowance
    other_allowances = Column(Float, default=0)

    # Deductions breakdown
    gosi_deduction = Column(Float, default=0)        # NEW: Social insurance (GOSI)
    tax_deduction = Column(Float, default=0)         # NEW: Income tax
    loan_deduction = Column(Float, default=0)        # NEW: Loan repayments
    absence_deduction = Column(Float, default=0)     # NEW: Absence/late deductions
    other_deductions = Column(Float, default=0)      # NEW: Other deductions

    # Legacy field (kept for backward compatibility, now computed)
    deductions = Column(Float, default=0)            # Total deductions

    # Net salary (computed)
    net_salary = Column(Float, nullable=False)

    employee = relationship("Employee", back_populates="payslips")


class Excuse(Base):
    """Excuse requests for late arrival or early departure."""
    __tablename__ = "excuses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String(10), ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    excuse_type = Column(Enum(ExcuseType), nullable=False)
    start_time = Column(Time, nullable=True)  # For late arrival
    end_time = Column(Time, nullable=True)    # For early departure
    reason = Column(Text, nullable=False)
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="excuses")


class Ticket(Base):
    """Support tickets/complaints submitted by employees."""
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String(10), ForeignKey("employees.id"), nullable=False)
    category = Column(String(50), nullable=False)  # e.g., "IT", "HR", "Facilities"
    description = Column(Text, nullable=False)
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="tickets")
