class ValidationUtils {
  static bool isPhoneNumberValid(String phone) {
    final phoneRegex = RegExp(r"^\+?[1-9]\d{1,14}$");
    return phoneRegex.hasMatch(phone);
  }

  static bool isPasswordStrong(String password) {
    return password.length >= 8;
  }
}
