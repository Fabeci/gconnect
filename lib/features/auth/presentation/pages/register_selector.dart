import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:gconnect/core/widgets/logo_widget.dart';
import 'package:go_router/go_router.dart';

class RegisterSelectorPage extends StatelessWidget {
  const RegisterSelectorPage({super.key});

  @override
  Widget build(BuildContext context) {
    Widget buildOption(String title, String svgIconPath, VoidCallback onTap) {
      return Container(
        height: 78,
        margin: const EdgeInsets.symmetric(vertical: 6),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey.shade300),
          borderRadius: BorderRadius.circular(12),
        ),
        child: ListTile(
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          leading: SvgPicture.asset(
            svgIconPath,
            width: 32,
            height: 32,
          ),
          title: Text(title),
          trailing: SvgPicture.asset(
            'assets/icons/arrow_right.svg', // Trailing SVG
            width: 20,
            height: 20,
          ),
          onTap: onTap,
        ),
      );
    }

    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.start,
          children: [
            const SizedBox(height: 40),
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
              "Inscrivez-vous en un clic !",
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              "Connectez-vous aux bonnes personnes, échangez, collaborez et faites avancer vos projets plus rapidement que jamais ! 🚀",
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 30),

            const Align(
              alignment: Alignment.centerLeft,
              child: Text(
                "M’inscrire en tant que :",
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
              ),
            ),
            const SizedBox(height: 12),

            buildOption("Etudiant", 'assets/icons/student.svg', () {
              context.go('/register-step1');
            }),
            buildOption("Alumni", 'assets/icons/alumni.svg', () {}),
            buildOption("Entreprise", 'assets/icons/company.svg', () {
              _showEntrepriseModal(context);
            }),

            const SizedBox(height: 20),
            TextButton(
              onPressed: () {
                context.go('/login');
              },
              child: const Text.rich(
                TextSpan(
                  text: "Vous avez déjà un compte ? ",
                  style: TextStyle(color: Colors.black),
                  children: [
                    TextSpan(
                      text: "Connectez-vous !",
                      style: TextStyle(color: Colors.blue),
                    ),
                  ],
                ),
                textAlign: TextAlign.center,
              ),
            )
          ],
        ),
      ),
    );
  }

  void _showEntrepriseModal(BuildContext context) {
  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
    ),
    builder: (_) {
      return Padding(
        padding: const EdgeInsets.fromLTRB(20, 24, 20, 40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey[300],
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 24),

            // Icône + Texte "Entreprise"
            Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                SvgPicture.asset(
                  'assets/icons/company.svg',
                  width: 28,
                  height: 28,
                  color: Colors.blue,
                ),
                const SizedBox(height: 8),
                const Text(
                  "Entreprise",
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ],
            ),

            const SizedBox(height: 20),
            const Text(
              "Pour la création de votre compte, veuillez\nnous contacter sur ce numéro",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 15, color: Colors.black54),
            ),
            const SizedBox(height: 20),

            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey.shade300),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.phone, size: 20),
                  SizedBox(width: 8),
                  Text(
                    "+33 763 87 03 87",
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    },
  );
}

}
