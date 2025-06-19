class Establishment {
  final String name;
  final String description;
  final String logoUrl;
  final String banner;
  final int memberCount;
  final List<String> relationAvatars;

  Establishment({
    required this.name,
    required this.description,
    required this.banner,
    required this.logoUrl,
    required this.memberCount,
    required this.relationAvatars,
  });
}
