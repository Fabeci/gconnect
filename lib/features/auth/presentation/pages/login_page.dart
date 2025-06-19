import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:gconnect/core/constants/theme_constants.dart';
import 'package:gconnect/core/widgets/custom_text_field.dart';
import 'package:gconnect/core/widgets/logo_widget.dart';
import 'package:gconnect/core/widgets/primary_button.dart';
import 'package:go_router/go_router.dart';

class LoginPage extends StatelessWidget {
  const LoginPage({super.key});

  @override
  Widget build(BuildContext context) {
    // Changer la couleur de la barre de statut (batterie, heure, etc.)
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.white, // ou ThemeConstants.primaryColor si tu veux
        statusBarIconBrightness: Brightness.dark,
      ),
    );

    return Scaffold(
      backgroundColor: Colors.white,
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.start,
          children: [
            const SizedBox(height: 40),
            // Flèche + Logo sur la même ligne
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                IconButton(
                  icon: const Icon(Icons.arrow_back),
                  onPressed: () {
                    context.go('/onboarding');
                  },
                ),
                const SizedBox(width: 12),
                const LogoWidget(),
              ],
            ),

            const SizedBox(height: 30),

            const Text(
              "Content de vous revoir ! Connectez-vous.",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 20),

            const CustomTextField(label: "Email"),
            const SizedBox(height: 10),
            const CustomTextField(label: "Mot de passe", isPassword: true),

            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: () {},
                child: RichText(
                  text: const TextSpan(
                    text: "Mot de passe oublié ? ",
                    style: TextStyle(color: Colors.black),
                    children: [
                      TextSpan(
                        text: "Récupérer",
                        style: TextStyle(color: ThemeConstants.primaryColor),
                      ),
                    ],
                  ),
                ),
              ),

            ),

            const SizedBox(height: 10),
            PrimaryButton(label: "Connexion", onPressed: () {context.go('/home-loading');}),
            const SizedBox(height: 10),

            TextButton(
              onPressed: () {},
              child: RichText(
                text: const TextSpan(
                  text: "Vous n'avez pas de compte ? ",
                  style: TextStyle(color: Colors.black),
                  children: [
                    TextSpan(
                      text: "S'inscrire",
                      style: TextStyle(color: ThemeConstants.primaryColor),
                    ),
                  ],
                ),
              ),
            ),

          ],
        ),
      ),
    );
  }
}
