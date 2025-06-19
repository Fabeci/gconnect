import 'package:flutter/material.dart';
import 'package:gconnect/core/widgets/custom_sccafold_widget.dart';
import 'package:gconnect/core/widgets/post_item_widget.dart';
import 'package:gconnect/features/home/presentations/widgets/profil_card_widget.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> with SingleTickerProviderStateMixin {
  final ScrollController _scrollController = ScrollController();
  final List<int> _postIndexes = List.generate(3, (index) => index);
  bool _isLoadingMore = false;

  late AnimationController _animationController;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_handleScroll);

    // Animation pour ProfileSuggestionsSection
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 700),
    );

    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, -0.2),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeOut,
    ));

    _fadeAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeIn,
    ));

    _animationController.forward();
  }

  void _handleScroll() {
    if (_scrollController.position.pixels >=
            _scrollController.position.maxScrollExtent - 100 &&
        !_isLoadingMore) {
      _loadMorePosts();
    }
  }

  void _loadMorePosts() async {
    setState(() {
      _isLoadingMore = true;
    });

    await Future.delayed(const Duration(seconds: 1));

    final nextPosts = List.generate(3, (index) => _postIndexes.length + index);
    setState(() {
      _postIndexes.addAll(nextPosts);
      _isLoadingMore = false;
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return CustomScaffold(
      body: ListView(
        controller: _scrollController,
        padding: const EdgeInsets.only(bottom: 80),
        children: [
          SlideTransition(
            position: _slideAnimation,
            child: FadeTransition(
              opacity: _fadeAnimation,
              child: const ProfileSuggestionsSection(),
            ),
          ),
          ..._postIndexes.map((index) {
            return AnimatedOpacity(
              opacity: 1,
              duration: const Duration(milliseconds: 1000),
              curve: Curves.easeIn,
              child: const PostItem(),
            );
          }),
          if (_isLoadingMore)
            const Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator()),
            ),
        ],
      ),
    );
  }
}

class ProfileSuggestionsSection extends StatelessWidget {
  const ProfileSuggestionsSection({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 2, vertical: 8),
          child: Text(
            'Personnes ayant fréquenté la même université',
            style: TextStyle(fontWeight: FontWeight.w500),
          ),
        ),
        SizedBox(
          height: 220,
          child: ListView(
            scrollDirection: Axis.horizontal,
            children: List.generate(4, (index) {
              return ProfileCard(
                name: "Nom $index",
                relations: 10 + index * 5,
                avatarPath: 'assets/images/home/user${index + 1}.png',
                relationAvatars: const [
                  'assets/images/home/user1.png',
                  'assets/images/home/user2.png',
                  'assets/images/home/user3.png',
                ],
                onRemove: () {
                  // Action à faire quand on clique sur le bouton supprimer
                },
              );
            }),
          ),
        ),
      ],
    );
  }
}
