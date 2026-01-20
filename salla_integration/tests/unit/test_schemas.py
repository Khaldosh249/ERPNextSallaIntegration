"""
Unit tests for validation schemas.
"""

import unittest
from salla_integration.models.schemas.product_schema import ProductSchema
from salla_integration.models.schemas.customer_schema import CustomerSchema


class TestProductSchema(unittest.TestCase):
    """Test cases for ProductSchema."""
    
    def test_validate_for_salla_valid(self):
        """Test valid product data."""
        data = {
            "name": "Test Product",
            "price": 100,
            "quantity": 50
        }
        
        result = ProductSchema.validate_for_salla(data)
        
        self.assertTrue(result["is_valid"])
        self.assertEqual(len(result["errors"]), 0)
    
    def test_validate_for_salla_missing_name(self):
        """Test missing required field."""
        data = {
            "price": 100
        }
        
        result = ProductSchema.validate_for_salla(data)
        
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("name" in e for e in result["errors"]))
    
    def test_validate_for_salla_negative_price(self):
        """Test negative price validation."""
        data = {
            "name": "Test",
            "price": -50
        }
        
        result = ProductSchema.validate_for_salla(data)
        
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("negative" in e.lower() for e in result["errors"]))
    
    def test_validate_for_salla_negative_quantity(self):
        """Test negative quantity validation."""
        data = {
            "name": "Test",
            "price": 50,
            "quantity": -10
        }
        
        result = ProductSchema.validate_for_salla(data)
        
        self.assertFalse(result["is_valid"])
    
    def test_sanitize_for_salla(self):
        """Test sanitizing data for Salla API."""
        data = {
            "name": "Product",
            "price": 100,
            "invalid_field": "should be removed",
            "description": "Valid field"
        }
        
        result = ProductSchema.sanitize_for_salla(data)
        
        self.assertIn("name", result)
        self.assertIn("price", result)
        self.assertIn("description", result)
        self.assertNotIn("invalid_field", result)



class TestCustomerSchema(unittest.TestCase):
    """Test cases for CustomerSchema."""
    
    def test_valid_email(self):
        """Test valid email validation."""
        data = {
            "customer_name": "Test Customer",
            "email": "test@example.com"
        }
        
        result = CustomerSchema.validate_for_erpnext(data)
        
        self.assertTrue(result["is_valid"])
    
    def test_invalid_email(self):
        """Test invalid email validation."""
        data = {
            "customer_name": "Test Customer",
            "_email": "invalid-email"
        }
        
        result = CustomerSchema.validate_for_erpnext(data)
        
        self.assertFalse(result["is_valid"])


if __name__ == "__main__":
    unittest.main()
