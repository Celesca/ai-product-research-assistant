"""
Tests for price analysis tool functions.
These test the deterministic calculation functions.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.tools.price_analysis import calculate_margin, calculate_profit, calculate_markup


class TestCalculateMargin:
    """Tests for the calculate_margin function."""
    
    def test_normal_margin(self):
        """Test margin calculation with normal values."""
        # margin = ((100 - 60) / 100) * 100 = 40%
        assert calculate_margin(100.0, 60.0) == 40.0
    
    def test_high_margin(self):
        """Test high margin calculation."""
        # margin = ((200 - 50) / 200) * 100 = 75%
        assert calculate_margin(200.0, 50.0) == 75.0
    
    def test_low_margin(self):
        """Test low margin calculation."""
        # margin = ((50 - 45) / 50) * 100 = 10%
        assert calculate_margin(50.0, 45.0) == 10.0
    
    def test_zero_cost(self):
        """Test margin when cost is zero (100% margin)."""
        # margin = ((100 - 0) / 100) * 100 = 100%
        assert calculate_margin(100.0, 0.0) == 100.0
    
    def test_zero_price(self):
        """Test margin when price is zero (should handle gracefully)."""
        assert calculate_margin(0.0, 50.0) == 0.0
    
    def test_negative_margin(self):
        """Test when cost exceeds price (loss)."""
        # margin = ((100 - 120) / 100) * 100 = -20%
        assert calculate_margin(100.0, 120.0) == -20.0
    
    def test_decimal_precision(self):
        """Test margin with decimal values."""
        # margin = ((129.99 - 65.00) / 129.99) * 100 ≈ 49.996%
        margin = calculate_margin(129.99, 65.00)
        assert 49.99 < margin < 50.01


class TestCalculateProfit:
    """Tests for the calculate_profit function."""
    
    def test_positive_profit(self):
        """Test profit calculation with positive result."""
        assert calculate_profit(100.0, 60.0) == 40.0
    
    def test_negative_profit(self):
        """Test profit when cost exceeds price (loss)."""
        assert calculate_profit(100.0, 120.0) == -20.0
    
    def test_zero_profit(self):
        """Test profit when price equals cost."""
        assert calculate_profit(100.0, 100.0) == 0.0
    
    def test_decimal_values(self):
        """Test profit with decimal values."""
        assert calculate_profit(129.99, 65.00) == 64.99


class TestCalculateMarkup:
    """Tests for the calculate_markup function."""
    
    def test_normal_markup(self):
        """Test markup calculation."""
        # markup = ((100 - 60) / 60) * 100 ≈ 66.67%
        markup = calculate_markup(100.0, 60.0)
        assert 66.6 < markup < 66.7
    
    def test_high_markup(self):
        """Test high markup."""
        # markup = ((200 - 50) / 50) * 100 = 300%
        assert calculate_markup(200.0, 50.0) == 300.0
    
    def test_zero_cost(self):
        """Test markup when cost is zero (should handle gracefully)."""
        assert calculate_markup(100.0, 0.0) == 0.0
    
    def test_zero_price(self):
        """Test markup when price is zero."""
        # markup = ((0 - 50) / 50) * 100 = -100%
        assert calculate_markup(0.0, 50.0) == -100.0


class TestMarginMarkupRelationship:
    """Tests verifying the relationship between margin and markup."""
    
    def test_margin_markup_consistency(self):
        """
        Test that margin and markup are consistent.
        If margin = 40%, then markup = 40/60 * 100 ≈ 66.67%
        """
        price = 100.0
        cost = 60.0
        
        margin = calculate_margin(price, cost)
        markup = calculate_markup(price, cost)
        
        # Verify: margin / (100 - margin) * 100 should equal markup
        expected_markup = (margin / (100 - margin)) * 100
        assert abs(markup - expected_markup) < 0.01
    
    def test_various_scenarios(self):
        """Test multiple price/cost scenarios."""
        scenarios = [
            (100, 50, 50.0, 100.0),    # 50% margin, 100% markup
            (100, 80, 20.0, 25.0),     # 20% margin, 25% markup
            (100, 25, 75.0, 300.0),    # 75% margin, 300% markup
        ]
        
        for price, cost, expected_margin, expected_markup in scenarios:
            margin = calculate_margin(price, cost)
            markup = calculate_markup(price, cost)
            
            assert abs(margin - expected_margin) < 0.01
            assert abs(markup - expected_markup) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
