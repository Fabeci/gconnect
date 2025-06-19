import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

void showJoinEstablishmentModal(BuildContext context) {
  final TextEditingController codeController = TextEditingController();

  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
    ),
    builder: (_) {
      return Padding(
        padding: EdgeInsets.only(
          left: 20,
          right: 20,
          top: 24,
          bottom: MediaQuery.of(context).viewInsets.bottom + 40,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Trait en haut
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey[300],
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 24),

            // Titre
            const Text(
              "Saisir votre code de l'établissement",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),

            const Text(
              "Lorem ipsum dolor sit amet, consectetur\nadipiscing elit, sed do eiusmod tempor incididunt.",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 15, color: Colors.black54),
            ),
            const SizedBox(height: 24),

            // Champ code
            Align(
              alignment: Alignment.centerLeft,
              child: Text("Code :", style: TextStyle(fontSize: 15)),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: codeController,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                filled: true,
                fillColor: Colors.grey[100],
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16),
              ),
            ),

            const SizedBox(height: 24),

            // Bouton rejoindre
            ElevatedButton(
              onPressed: () {
                // Implémente ta logique ici
              },
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 60),
                backgroundColor: Colors.blue,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(32),
                ),
              ),
              child: const Text("Rejoindre", style: TextStyle(fontSize: 16)),
            ),

            const SizedBox(height: 16),

            // Bouton Scan QR code
            TextButton.icon(
              onPressed: () {
                // Appelle ici ton scanner de QR code
              },
              icon: const Icon(Icons.qr_code_scanner, color: Colors.blue),
              label: const Text(
                "Scanner un QR code",
                style: TextStyle(color: Colors.blue, fontSize: 15),
              ),
            ),
          ],
        ),
      );
    },
  );
}
