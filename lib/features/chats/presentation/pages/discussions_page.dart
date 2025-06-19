import 'package:flutter/material.dart';
import 'package:gconnect/core/constants/theme_constants.dart';
import 'package:go_router/go_router.dart';
import 'package:gconnect/features/chats/presentation/widgets/discussion_item_widget.dart';

class DiscussionsPage extends StatefulWidget {
  const DiscussionsPage({super.key});

  @override
  State<DiscussionsPage> createState() => _DiscussionsPageState();
}

class _DiscussionsPageState extends State<DiscussionsPage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        leading: Navigator.of(context).canPop()
            ? IconButton(
                icon: const Icon(Icons.arrow_back, color: Colors.black),
                onPressed: () => context.pop(),
              )
            : null,
        title: Row(
          children: [
            
            const Text(
              "Discussions",
              style: TextStyle(color: Colors.black),
            ),
            const SizedBox(width: 8),
            Image.asset(
                'assets/images/logo/logo_icon.png',
                height: 64,
              ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.more_horiz, color: Colors.black),
            onPressed: () {
              // Action à définir
              showModalBottomSheet(
                context: context,
                builder: (context) => const SizedBox(
                  height: 150,
                  child: Center(child: Text("Options supplémentaires")),
                ),
              );
            },
          ),
        ],
      ),
      body: Column(
        children: [
          _buildSearchBar(),
          _buildTabBar(),
          const Divider(height: 1),
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildDiscussionsList(),
                _buildDiscussionsList(),
                _buildDiscussionsList(),
              ],
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          context.pushNamed('new_discussion'); // Assure-toi que cette route existe
        },
        backgroundColor: ThemeConstants.primaryColor,
        child: IconButton(
          icon: Image.asset("assets/icons/message.png", width: 20, height: 20, color: ThemeConstants.whiteColor,),
          color: ThemeConstants.whiteColor,
          onPressed: (){
            context.push("/new-discussion");
          },
        ), // Icône stylée pour écrire un nouveau message
      ),
    );
  }

  Widget _buildSearchBar() {
    return const Padding(
      padding: EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: TextField(
        decoration: InputDecoration(
          hintText: 'Rechercher un message',
          prefixIcon: Icon(Icons.search),
          filled: true,
          fillColor: Color(0xFFF0F0F0),
          contentPadding: EdgeInsets.symmetric(vertical: 0),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.all(Radius.circular(24)),
            borderSide: BorderSide.none,
          ),
        ),
      ),
    );
  }

  Widget _buildTabBar() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8.0),
      child: TabBar(
        isScrollable: true,
        indicatorColor: Colors.blue,
        labelColor: Colors.black,
        unselectedLabelColor: Colors.grey,
        controller: _tabController,
        tabs: const [
          Tab(text: 'Toutes'),
          Tab(text: 'Discussions privées'),
          Tab(text: 'Groupe(s)'),
        ],
      ),
    );
  }

  Widget _buildDiscussionsList() {
    return ListView(
      children: const [
        DiscussionItemWidget(
          name: 'Seynabou Diagne',
          subtitle: 'Le Lorem Ipsum est simplement du faux...',
          date: 'En ligne',
          imagePath: 'assets/images/home/user1.png',
          isOnline: true,
          unreadCount: 1,
        ),
        DiscussionItemWidget(
          name: 'Alpha Conde',
          subtitle: 'Le Lorem Ipsum est simplement du faux...',
          date: 'Il y’a un jour',
          imagePath: 'assets/images/home/user2.png',
        ),
        // Ajoute d'autres éléments ici...
      ],
    );
  }
}
