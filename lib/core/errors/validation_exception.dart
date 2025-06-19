import 'package:gconnect/core/errors/app_exception.dart';

class ValidationException extends AppException {
  ValidationException(String message) : super(message);
}
