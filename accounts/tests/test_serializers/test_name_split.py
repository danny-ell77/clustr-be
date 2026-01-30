from django.test import TestCase
from accounts.models import AccountUser
from accounts.serializers import AccountSerializer


class NameSplitSerializerTestCase(TestCase):
    
    def test_output_splits_name(self):
        """Test that serializer output splits name into first/last and keeps name"""
        user = AccountUser.objects.create_owner(
            email_address="test@example.com",
            password="TestPass123!",
            name="John Smith"
        )
        serializer = AccountSerializer(user)
        
        self.assertEqual(serializer.data['first_name'], 'John')
        self.assertEqual(serializer.data['last_name'], 'Smith')
        self.assertEqual(serializer.data['name'], 'John Smith')
    
    def test_input_combines_names(self):
        """Test that serializer input combines first/last into name"""
        data = {
            'email_address': 'test@example.com',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'phone_number': '+2348000000000'
        }
        serializer = AccountSerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['name'], 'Jane Doe')
    
    def test_single_name_handling(self):
        """Test handling of single names"""
        user = AccountUser.objects.create_owner(
            email_address="test@example.com",
            password="TestPass123!",
            name="Madonna"
        )
        serializer = AccountSerializer(user)
        
        self.assertEqual(serializer.data['first_name'], 'Madonna')
        self.assertEqual(serializer.data['last_name'], '')
    
    def test_multiple_names(self):
        """Test handling of multiple name parts"""
        user = AccountUser.objects.create_owner(
            email_address="test@example.com",
            password="TestPass123!",
            name="Mary Jane Watson"
        )
        serializer = AccountSerializer(user)
        
        self.assertEqual(serializer.data['first_name'], 'Mary')
        self.assertEqual(serializer.data['last_name'], 'Jane Watson')
    
    def test_empty_last_name_input(self):
        """Test that only first name is acceptable"""
        data = {
            'email_address': 'test@example.com',
            'first_name': 'Prince',
            'last_name': '',
            'phone_number': '+2348000000000'
        }
        serializer = AccountSerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['name'], 'Prince')
    
    def test_both_names_empty_fails(self):
        """Test that empty names are rejected"""
        data = {
            'email_address': 'test@example.com',
            'first_name': '',
            'last_name': '',
            'phone_number': '+2348000000000'
        }
        serializer = AccountSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('first_name', serializer.errors)
