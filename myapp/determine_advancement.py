

# def determine_advancement(rank, user_league, total_users, promotion_threshold, demotion_threshold, league):
#     user = user_league.user
#     is_highest_league = league.league.order == 10
#     is_lowest_league = league.league.order == 1

#     if is_highest_league:
#         gems_obtained = 10
#         status = "Retained"
#         retain_user(user, gems_obtained, league)
#     elif is_lowest_league:
#         if rank <= promotion_threshold:
#             gems_obtained = 20 - (rank - 1) * 2
#             status = "Promoted"
#             promote_user(user, gems_obtained, league)
#         else:
#             gems_obtained = 10 if user_league.xp_global > 0 else 0
#             status = "Retained"
#             retain_user(user, gems_obtained, league)
#     else:
#         if total_users <= 3:
#             if user_league.xp_global == 0:
#                 gems_obtained = 0
#                 status = "Demoted"
#                 demote_user(user, gems_obtained, league)
#             else:
#                 gems_obtained = 10
#                 status = "Retained"
#                 retain_user(user, gems_obtained, league)
#         else:
#             if rank <= promotion_threshold:
#                 gems_obtained = 20 - (rank - 1) * 2
#                 status = "Promoted"
#                 promote_user(user, gems_obtained, league)
#             elif rank <= demotion_threshold:
#                 gems_obtained = 10
#                 status = "Retained"
#                 retain_user(user, gems_obtained, league)
#             else:
#                 gems_obtained = 0
#                 status = "Demoted"
#                 demote_user(user, gems_obtained, league)

#     return status, gems_obtained
