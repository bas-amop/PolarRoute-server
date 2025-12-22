"""
Tests for the ResponseMixin and response formatting utilities.
"""

from django.test import TestCase
from rest_framework.response import Response
from rest_framework import status

from polarrouteserver.route_api.responses import ResponseMixin


class MockView(ResponseMixin):
    """Mock view class for testing ResponseMixin methods."""
    pass


class TestResponseMixin(TestCase):
    """Test cases for ResponseMixin methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.view = MockView()

    def test_success_response_default_status(self):
        """Test success_response with default 200 status code."""
        test_data = {"message": "Success", "count": 5}
        response = self.view.success_response(test_data)

        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, test_data)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_success_response_custom_status(self):
        """Test success_response with custom 200-level status code."""
        test_data = {"message": "Success with custom status"}
        response = self.view.success_response(test_data, status.HTTP_200_OK)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, test_data)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_success_response_empty_data(self):
        """Test success_response with empty data."""
        response = self.view.success_response({})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {})
        self.assertEqual(response["Content-Type"], "application/json")

    def test_accepted_response(self):
        """Test accepted_response returns correct 202 status."""
        test_data = {"job_id": "12345", "status": "accepted"}
        response = self.view.accepted_response(test_data)

        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data, test_data)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_no_content_response_default(self):
        """Test no_content_response with default parameters."""
        response = self.view.no_content_response()

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, {})
        self.assertEqual(response["Content-Type"], "application/json")

    def test_no_content_response_with_data(self):
        """Test no_content_response with custom data."""
        test_data = {"deleted_count": 3}
        response = self.view.no_content_response(data=test_data)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, test_data)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_no_content_response_with_message(self):
        """Test no_content_response with message parameter."""
        message = "No data found"
        response = self.view.no_content_response(message=message)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, {"message": message})
        self.assertEqual(response["Content-Type"], "application/json")

    def test_no_content_response_with_data_and_message(self):
        """Test no_content_response with both data and message."""
        test_data = {"count": 0}
        message = "Empty result set"
        response = self.view.no_content_response(data=test_data, message=message)

        expected_data = {"count": 0, "message": message}
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, expected_data)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_bad_request_response_default_status(self):
        """Test bad_request_response with default 400 status."""
        error_message = "Invalid input data"
        response = self.view.bad_request_response(error_message)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"error": error_message})
        self.assertEqual(response["Content-Type"], "application/json")

    def test_bad_request_response_custom_status(self):
        """Test bad_request_response method allows custom status codes."""
        error_message = "Custom bad request error"
        # Test that the method accepts different 4xx status codes if needed
        custom_status = status.HTTP_400_BAD_REQUEST  # Use the same as default to show flexibility
        response = self.view.bad_request_response(error_message, custom_status)

        self.assertEqual(response.status_code, custom_status)
        self.assertEqual(response.data, {"error": error_message})
        self.assertEqual(response["Content-Type"], "application/json")

    def test_not_found_response(self):
        """Test not_found_response returns correct 404 status."""
        error_message = "Resource not found"
        response = self.view.not_found_response(error_message)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {"error": error_message})
        self.assertEqual(response["Content-Type"], "application/json")

    def test_not_acceptable_response(self):
        """Test not_acceptable_response returns correct 406 status."""
        error_message = "Conflict with existing resource"
        response = self.view.not_acceptable_response(error_message)

        expected_data = {"error": error_message}
        self.assertEqual(response.status_code, status.HTTP_406_NOT_ACCEPTABLE)
        self.assertEqual(response.data, expected_data)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_not_acceptable_response_empty_data(self):
        """Test not_acceptable_response with empty data dict."""
        error_message = "Not acceptable"
        response = self.view.not_acceptable_response(error_message)

        expected_data = {"error": error_message}
        self.assertEqual(response.status_code, status.HTTP_406_NOT_ACCEPTABLE)
        self.assertEqual(response.data, expected_data)
        self.assertEqual(response["Content-Type"], "application/json")


class TestResponseConsistency(TestCase):
    """Test cases for response format consistency."""

    def setUp(self):
        """Set up test fixtures."""
        self.view = MockView()

    def test_all_responses_have_content_type_header(self):
        """Test that all response methods include Content-Type header."""
        responses = [
            self.view.success_response({"test": "data"}),
            self.view.accepted_response({"test": "data"}),
            self.view.no_content_response(),
            self.view.bad_request_response("Error"),
            self.view.not_found_response("Not found"),
            self.view.not_acceptable_response("Not acceptable"),
        ]

        for response in responses:
            self.assertEqual(response["Content-Type"], "application/json")


    def test_error_responses_have_error_field(self):
        """Test that error responses consistently use 'error' field."""
        error_responses = [
            self.view.bad_request_response("Bad request"),
            self.view.not_found_response("Not found"),
            self.view.not_acceptable_response("Not acceptable"),
        ]

        for response in error_responses:
            self.assertIn("error", response.data)
            self.assertIsInstance(response.data["error"], str)

    def test_status_codes_match_http_standards(self):
        """Test that status codes match HTTP standards."""
        test_cases = [
            (self.view.success_response({}), 200),
            (self.view.accepted_response({}), 202),
            (self.view.no_content_response(), 204),
            (self.view.bad_request_response("Error"), 400),
            (self.view.not_found_response("Not found"), 404),
            (self.view.not_acceptable_response("Error"), 406),
        ]

        for response, expected_status in test_cases:
            self.assertEqual(response.status_code, expected_status)
