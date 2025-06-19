import 'package:flutter/material.dart';
import 'package:gconnect/core/constants/theme_constants.dart';
import 'package:go_router/go_router.dart';

import 'package:gconnect/core/widgets/logo_widget.dart';
import 'package:gconnect/core/widgets/custom_text_field.dart';
import 'package:gconnect/core/widgets/primary_button.dart';

class RegisterStep1Page extends StatefulWidget {
  const RegisterStep1Page({super.key});

  @override
  State<RegisterStep1Page> createState() => _RegisterStep1PageState();
}

class _RegisterStep1PageState extends State<RegisterStep1Page> {
  String gender = "Masculin";

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 40),
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back),
                    onPressed: () {
                      context.go('/register');
                    },
                  ),
                  const SizedBox(width: 12),
                  const LogoWidget(),
                ],
              ),
              const SizedBox(height: 10),
              const Text(
                "Inscrivez-vous en un clic !",
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              LinearProgressIndicator(
                value: 0.50, // 1 étape sur 3
                backgroundColor: Colors.grey.shade300,
                color: ThemeConstants.primaryColor,
                minHeight: 2,
              ),
              const SizedBox(height: 30),

              const CustomTextField(label: "Prénom"),
              const SizedBox(height: 10),
              const CustomTextField(label: "Nom"),
              const SizedBox(height: 10),
              const CustomTextField(label: "Email"),
              const SizedBox(height: 10),
              const CustomTextField(label: "Mot de passe", isPassword: true),
              const SizedBox(height: 10),
              const CustomTextField(label: "N° Téléphone"),
              const SizedBox(height: 20),

              const Text(
                "Sexe",
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
              ),
              const SizedBox(height: 6),
              Row(
                children: [
                  Radio<String>(
                    value: "Masculin",
                    groupValue: gender,
                    onChanged: (value) {
                      setState(() {
                        gender = value!;
                      });
                    },
                  ),
                  const Text("Masculin"),
                  const SizedBox(width: 10),
                  Radio<String>(
                    value: "Feminin",
                    groupValue: gender,
                    onChanged: (value) {
                      setState(() {
                        gender = value!;
                      });
                    },
                  ),
                  const Text("Feminin"),
                ],
              ),

              const SizedBox(height: 30),

              PrimaryButton(
                label: "Suivant",
                onPressed: () {
                  context.go('/register-step2');
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
