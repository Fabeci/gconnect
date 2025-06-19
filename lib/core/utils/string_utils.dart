class StringUtils {
  static bool isEmailValid(String email) {
    final emailRegex = RegExp(r"^[a-zA-Z0-9]+@[a-zA-Z0-9]+\.[a-zA-Z]+");
    return emailRegex.hasMatch(email);
  }

  static String capitalize(String text) {
    if (text.isEmpty) return text;
    return text[0].toUpperCase() + text.substring(1);
  }

  static String truncate(String text, {int length = 30}) {
    if (text.length <= length) return text;
    return '${text.substring(0, length)}...';
  }
}
