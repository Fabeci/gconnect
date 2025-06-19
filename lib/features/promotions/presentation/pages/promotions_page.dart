import 'package:flutter/material.dart';
import 'package:gconnect/core/widgets/custom_sccafold_widget.dart';
import 'package:gconnect/features/promotions/data/models/promotion_model.dart';
import 'package:gconnect/features/promotions/presentation/widgets/promotion_card.dart';
import 'package:go_router/go_router.dart';

class PromotionsPage extends StatelessWidget {
  final List<Promotion> promotions = [
    Promotion(
      title: "Fac Médecine (UCAD)",
      subtitle: "1ère année 2019",
      description:
          "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt.",
      memberCount: 45,
    ),
    Promotion(
      title: "Departement Informatique (ESP)",
      subtitle: "3ème année 2024",
      description:
          "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt.",
      memberCount: 45,
    ),
    Promotion(
      title: "Departement de Gestion (ESM)",
      subtitle: "Master 1 année 2019",
      description:
          "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt.",
      memberCount: 45,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: CustomScaffold(
        body: Column(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.grey[200],
                borderRadius: BorderRadius.circular(32),
              ),
              child: const TextField(
                decoration: InputDecoration(
                  icon: Icon(Icons.search),
                  border: InputBorder.none,
                  hintText: 'Rechercher un promotionnaire...',
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Row(
                children: [
                  const Expanded(
                    child: TabBar(
                      indicatorColor: Colors.blue,
                      labelColor: Colors.blue,
                      unselectedLabelColor: Colors.grey,
                      isScrollable: true, // largeur selon texte
                      indicatorSize: TabBarIndicatorSize.label, // bordure = largeur texte
                      tabs: [
                        Tab(text: "Tout"),
                        Tab(text: "Mes promos"),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.filter_list),
                    onPressed: () {
                      // Ajoute ici le comportement du filtre si nécessaire
                    },
                  )
                ],
              ),
            ),
            Expanded(
              child: TabBarView(
                children: [
                  buildPromotionList(context),
                  const Center(child: Text("Aucune promotion rejointe.")),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget buildPromotionList(BuildContext context) {
    return ListView.builder(
      itemCount: promotions.length,
      itemBuilder: (context, index) {
        final promotion = promotions[index];
        return InkWell(
          onTap: () {
            context.push('/promotionnaires');
          },
          child: Column(
            children: [
              PromotionCard(promotion: promotion),
              const Divider(height: 1), // Bordure en bas
            ],
          ),
        );
      },
    );
  }
}
