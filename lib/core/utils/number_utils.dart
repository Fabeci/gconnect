class NumberUtils {
  static String formatCurrency(double amount) {
    return '\$${amount.toStringAsFixed(2)}';
  }

  static bool isEven(int number) {
    return number % 2 == 0;
  }

  static bool isOdd(int number) {
    return number % 2 != 0;
  }
}
