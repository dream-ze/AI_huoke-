from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token
from app.schemas import (
    CustomerCreate, 
    CustomerUpdate, 
    CustomerFollowRecord,
    CustomerResponse
)
from app.services import CustomerService

router = APIRouter(prefix="/api/customer", tags=["customer"])


@router.post("/create", response_model=CustomerResponse)
def create_customer(
    customer_data: CustomerCreate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Create new customer"""
    customer = CustomerService.create_customer(db, current_user["user_id"], customer_data)
    return customer


@router.get("/list")
def list_customers(
    status: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """List user's customers"""
    customers = CustomerService.get_user_customers(
        db, current_user["user_id"], status, skip, limit
    )
    return customers


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get specific customer"""
    customer = CustomerService.get_customer(db, current_user["user_id"], customer_id)
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    customer_data: CustomerUpdate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Update customer"""
    customer = CustomerService.update_customer(
        db, current_user["user_id"], customer_id, customer_data
    )
    return customer


@router.post("/{customer_id}/follow")
def add_follow_record(
    customer_id: int,
    record: CustomerFollowRecord,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Add follow-up record"""
    customer = CustomerService.add_follow_record(
        db, current_user["user_id"], customer_id, record.content
    )
    return customer


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Delete customer"""
    CustomerService.delete_customer(db, current_user["user_id"], customer_id)
    return {"message": "Customer deleted successfully"}


@router.get("/pending/list")
def get_pending_follow_customers(
    limit: int = Query(20, le=100),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get customers pending follow-up"""
    customers = CustomerService.get_pending_follow_customers(db, current_user["user_id"], limit)
    return customers
