import 'package:flutter/material.dart';

class CustomTextField extends StatelessWidget {
  final String? label;
  final bool isPassword;
  final IconData? prefixIcon;

  const CustomTextField({
    super.key,
    this.label,
    this.isPassword = false,
    this.prefixIcon,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (label != null) ...[
          Text(
            label!,
            style: const TextStyle(fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 6),
        ],
        SizedBox(
          height: 50,
          child: TextField(
            obscureText: isPassword,
            decoration: InputDecoration(
              prefixIcon: prefixIcon != null ? Icon(prefixIcon) : null,
              suffixIcon: isPassword ? const Icon(Icons.visibility_off) : null,
              contentPadding: const EdgeInsets.symmetric(horizontal: 16),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(15),
              ),
            ),
          ),
        ),
      ],
    );
  }
}
