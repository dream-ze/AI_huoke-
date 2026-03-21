from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models import Customer, User
from app.schemas import CustomerCreate, CustomerUpdate
from fastapi import HTTPException, status
from datetime import datetime


class CustomerService:
    @staticmethod
    def create_customer(db: Session, user_id: int, customer_data: CustomerCreate) -> Customer:
        """Create new customer"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        customer = Customer(
            owner_id=user_id,
            **customer_data.model_dump()
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer

    @staticmethod
    def get_user_customers(
        db: Session, 
        user_id: int, 
        status: str = None,
        skip: int = 0, 
        limit: int = 100
    ) -> list:
        """Get user's customers"""
        query = db.query(Customer).filter(Customer.owner_id == user_id)
        
        if status:
            query = query.filter(Customer.customer_status == status)
        
        return query.order_by(desc(Customer.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def get_customer(db: Session, user_id: int, customer_id: int) -> Customer:
        """Get specific customer"""
        customer = db.query(Customer).filter(
            (Customer.id == customer_id) & (Customer.owner_id == user_id)
        ).first()
        
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        return customer

    @staticmethod
    def update_customer(
        db: Session, 
        user_id: int, 
        customer_id: int, 
        customer_data: CustomerUpdate
    ) -> Customer:
        """Update customer"""
        customer = CustomerService.get_customer(db, user_id, customer_id)
        
        update_data = customer_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(customer, field, value)
        
        db.commit()
        db.refresh(customer)
        return customer

    @staticmethod
    def add_follow_record(
        db: Session, 
        user_id: int, 
        customer_id: int, 
        content: str
    ) -> Customer:
        """Add follow-up record"""
        customer = CustomerService.get_customer(db, user_id, customer_id)
        
        if customer.follow_records is None:
            customer.follow_records = []
        
        customer.follow_records.append({
            "date": datetime.utcnow().isoformat(),
            "content": content,
            "owner": "default_user"
        })
        
        db.commit()
        db.refresh(customer)
        return customer

    @staticmethod
    def delete_customer(db: Session, user_id: int, customer_id: int) -> bool:
        """Delete customer"""
        customer = CustomerService.get_customer(db, user_id, customer_id)
        db.delete(customer)
        db.commit()
        return True

    @staticmethod
    def get_pending_follow_customers(db: Session, user_id: int, limit: int = 20) -> list:
        """Get customers pending follow-up"""
        return db.query(Customer).filter(
            (Customer.owner_id == user_id) &
            (Customer.customer_status.in_(["new", "pending_follow", "contacted"]))
        ).order_by(desc(Customer.created_at)).limit(limit).all()
