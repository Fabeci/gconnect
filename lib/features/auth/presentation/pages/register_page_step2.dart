import 'package:flutter/material.dart';
import 'package:gconnect/core/constants/theme_constants.dart';
import 'package:gconnect/core/widgets/logo_widget.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/widgets/custom_text_field.dart';
import '../../../../core/widgets/primary_button.dart';

class RegisterStep2Page extends StatelessWidget {
  const RegisterStep2Page({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 20),
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back),
                    onPressed: () {
                      context.go('/register-step1');
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
                value: 0.66, // Étape 2 sur 3
                backgroundColor: Colors.grey.shade300,
                color: ThemeConstants.primaryColor,
                minHeight: 2,
              ),
              const SizedBox(height: 30),
              DropdownButtonFormField<String>(
                decoration: const InputDecoration(
                  labelText: "Nom de l’Établissement",
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(value: "esi", child: Text("ESI")),
                  DropdownMenuItem(value: "esp", child: Text("ESP")),
                ],
                onChanged: (value) {},
              ),
              const SizedBox(height: 10),
              const CustomTextField(label: "Code de l’Établissement"),
              const SizedBox(height: 10),
              DropdownButtonFormField<String>(
                decoration: const InputDecoration(
                  labelText: "Année de promotion",
                  border: OutlineInputBorder(),
                ),
                items: List.generate(
                  10,
                  (index) {
                    final year = 2025 - index;
                    return DropdownMenuItem(
                      value: year.toString(),
                      child: Text(year.toString()),
                    );
                  },
                ),
                onChanged: (value) {},
              ),
              const SizedBox(height: 80), // Ajoute de l’espace pour éviter l'overlap avec le bouton
            ],
          ),
        ),
      ),
      bottomNavigationBar: Padding(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
        child: PrimaryButton(
          label: "Terminé",
          onPressed: () {
            // Action de fin d'inscription ici
          },
        ),
      ),
    );
  }
}
