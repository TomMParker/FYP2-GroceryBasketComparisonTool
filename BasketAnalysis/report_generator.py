import pandas as pd
from mysql.connector.utils import read_lc_int


class ReportGenerator:

    def create_final_table(self, df):
        # group by product_name and shop_name to ensure unique combinations
        grouped_df = df.groupby(['product_name', 'shop_name']).agg({
            'price': 'first',
            'price_zscore': 'first',
            'rating': 'first'
        }).reset_index()

        # pivot the table with shops at the top level
        final_table = grouped_df.pivot_table(
            index='product_name',
            columns='shop_name',
            values=['price', 'price_zscore', 'rating']
        )

        # reorder the column levels to have shop_name at the top
        final_table = final_table.swaplevel(0, 1, axis=1)

        # sort columns by shop name, then by metric
        shops = ['Asda', 'Aldi', 'Sainsburys', 'Tesco']
        metrics = ['price', 'price_zscore', 'rating']
        ordered_cols = pd.MultiIndex.from_product([shops, metrics])

        #filter to only include columns that exist
        existing_cols = [col for col in ordered_cols if col in final_table.columns]
        if existing_cols:
            final_table = final_table[existing_cols]

        return final_table

     # generates recommendation basend on wsm scores, user weights and statistical analysis
    # threshold arg determines what level a weighting is deemed important
    def generate_recommendation(self, wsm_scores, weights, preferences, price_friedman, rating_friedman, df,
                                threshold=0.33):

        if wsm_scores.empty:
            return "Not enough data to make a recommendation."

        best_shop = wsm_scores.loc[wsm_scores['wsm_score'].idxmax(), 'shop_name']

        # get user price difference threshold from weights df
        price_difference_threshold = weights.get('price_difference_threshold', 5.0)

        # check price differences between cheapest and most expensive stores
        store_totals = df.groupby('shop_name')['price'].sum().reset_index()
        cheapest_store = store_totals.loc[store_totals['price'].idxmin(), 'shop_name']
        most_expensive_store = store_totals.loc[store_totals['price'].idxmax(), 'shop_name']
        cheapest_price = store_totals['price'].min()
        most_expensive_price = store_totals['price'].max()
        price_difference = most_expensive_price - cheapest_price
        user_defined_significant_price_diff = price_difference > price_difference_threshold

        # calculate rating averages
        rating_by_shop = df.groupby('shop_name')['rating'].mean().reset_index()
        highest_rated_store = rating_by_shop.loc[rating_by_shop['rating'].idxmax(), 'shop_name']

        # check which factors are important to user
        price_important = weights['price_weight'] >= threshold
        quality_important = weights['quality_weight'] >= threshold
        convenience_important = weights['convenience_weight'] >= threshold

        # creates an array holding what factors a user deems important
        important_factors = []
        if price_important:
            important_factors.append("price")
        if quality_important:
            important_factors.append("quality")
        if convenience_important:
            important_factors.append("convenience")

        # format preference string, one weight will always be > 0.33
        if len(important_factors) == 1:
            preference_str = important_factors[0]
        elif len(important_factors) == 2:
            preference_str = f"{important_factors[0]} and {important_factors[1]}"
        else:
            preference_str = f"{', '.join(important_factors[:-1])}, and {important_factors[-1]}"

        # empty recommendation string
        recommendation = ""

        # booleans to check price or rating f tests have been done and are significant
        price_significant = price_friedman[1] < 0.05 if price_friedman[0] is not None else False
        rating_significant = rating_friedman[1] < 0.05 if rating_friedman[0] is not None else False

        # inform users if their heavily weighted factors are analysed to be important
        # if user cares about price and quality..
        if price_important and quality_important:
            # .. and both are significant:
            if price_significant and rating_significant:
                recommendation += "Statistical analysis confirms that both price and quality differences between shops are significant.\n " \
                                  "Your balanced preference for these factors aligns well with the observed differences between shops.\n"

            # .. price significant but not ratings
            elif price_significant and not rating_significant:
                recommendation += "Statistical analysis shows that price differences between shops are significant, but quality ratings are similar. \n" \
                                  "\nYour preference for both factors is balanced, so you might want to consider increasing your price weighting.\n"
            # .. price not significant but ratings are
            elif not price_significant and rating_significant:
                recommendation += "Statistical analysis shows that quality differences between shops are significant, while price patterns are less pronounced.\n "
                if user_defined_significant_price_diff:
                    recommendation += f"\nHowever, there is still a total basket price difference of £{price_difference:.2f} between {cheapest_store} (£{cheapest_price:.2f}) and {most_expensive_store} (£{most_expensive_price:.2f}).\n "
                recommendation += "\nYour preference for both factors is balanced, but you might want to consider increasing your quality weighting.\n"
            # .. neither significant
            else:
                recommendation += "While statistical tests don't show significant differences in price or quality patterns across all products, "
                if user_defined_significant_price_diff:
                    recommendation += f"there is a total basket price difference of £{price_difference:.2f} between {cheapest_store} (£{cheapest_price:.2f}) and {most_expensive_store} (£{most_expensive_price:.2f}), which may be meaningful to you.\n"
                else:
                    recommendation += "the shops offer fairly similar value based on your preferences.\n"

        # user care mainly about price:
        elif price_important and not quality_important:
            if price_significant:
                recommendation += "Statistical analysis confirms that price differences between shops are significant.\n "
                if cheapest_store != best_shop:
                    recommendation += f"\nEven though {cheapest_store} offers the lowest total price, your weightings towards convenience and ratings have influenced the final recommendation. "
                else:
                    recommendation += f"\nYour focus on price aligns well with the observed differences between shops. "
                recommendation += "\n"
            else:
                recommendation += "While statistical tests don't show significant price patterns across all products, "
                if user_defined_significant_price_diff:
                    recommendation += f"there is a substantial total basket price difference of £{price_difference:.2f} between {cheapest_store} (£{cheapest_price:.2f}) and {most_expensive_store} (£{most_expensive_price:.2f}).\n"

                    if cheapest_store != best_shop:
                        recommendation += f"\nEven though {cheapest_store} offers the lowest total price, your weightings towards convenience and ratings have influenced the final recommendation. "
                    else:
                        recommendation += f"\nThis aligns with your preference for price as the most important factor. "
                else:
                    recommendation += "and the total basket prices are quite similar across stores. " \
                                      "Since price is important to you, you may want to consider any of these shops as they offer similar value."
                recommendation += "\n"

        # user care mainly about quality:
        elif quality_important and not price_important:
            if rating_significant:
                recommendation += "Statistical analysis confirms that quality differences between shops are significant.\n " \
                                  "\nYour focus on quality aligns well with the observed differences between shops.\n"
            else:
                recommendation += "Statistical tests don't show significant quality differences across all products, "
                if user_defined_significant_price_diff:
                    recommendation += f"there is a substantial price difference of £{price_difference:.2f} between stores that you may want to consider.\n"

                    if highest_rated_store != best_shop:
                        recommendation += f"\nEven though {highest_rated_store} offers the highest average quality ratings, your weightings towards convenience and price have influenced the final recommendation. "
                else:
                    recommendation += "quality ratings are fairly similar across stores.\n " \
                                      "\nSince quality is important to you, you may want to consider any of these shops as they offer similar value."
                recommendation += "\n"

        else:
            # user cares mainly convenience over price and quality:
            if convenience_important:
                recommendation += "Based on your preferences, convenience appears to be your primary concern."
                if not price_significant and user_defined_significant_price_diff:
                    recommendation += f"\nNote that there is a price difference of £{price_difference:.2f} between {cheapest_store} and {most_expensive_store} for this basket, which you may want to consider alongside your convenience preference. "
                recommendation += "\n"
            else:
                recommendation += "Your preferences don't show a strong weighting toward any specific factor. " \
                                  "Consider adjusting your weightings to better reflect what's important to you.\n"

        # main shop recommendation
        recommendation += f"\nConsidering your overall preferences, the recommended shop for you to buy your goods at is: {best_shop}\n"


        return recommendation

    # adds comparison between preferred shop and best_shop if different
    def add_preferred_shop_comparison(self, recommendation, df, wsm_scores, preferences, best_shop):

        # store user shop preferences
        shop_preferences = {
            'Asda': preferences['asda_preference'],
            'Aldi': preferences['aldi_preference'],
            'Sainsburys': preferences['sainsburys_preference'],
            'Tesco': preferences['tesco_preference']
        }

        # find lowest number (lower number = higher pref)
        preferred_shop = min(shop_preferences.items(), key=lambda x: x[1])[0]

        # if preferred shop is not the best_shop - add comparison
        if preferred_shop != best_shop:
            # calculate price savings between best and prefered shop
            preferred_total = df[df['shop_name'] == preferred_shop]['price'].sum()
            best_shop_total = df[df['shop_name'] == best_shop]['price'].sum()
            price_savings = preferred_total - best_shop_total

            # calculate rating difference
            preferred_avg_rating = df[df['shop_name'] == preferred_shop]['rating'].mean()
            best_shop_avg_rating = df[df['shop_name'] == best_shop]['rating'].mean()
            rating_diff_pct = ((best_shop_avg_rating - preferred_avg_rating) / preferred_avg_rating * 100)

            comparison = f"\nYour preferred shop is {preferred_shop}, however if you were to switch to {best_shop} "

            # if there are price savings..
            if price_savings > 0:
                comparison += f"you would save £{price_savings:.2f} "

                # .. and quality is better
                if rating_diff_pct > 0:
                    comparison += f"and have an improvement in quality (based on ratings) of {rating_diff_pct:.1f}%."
                # .. but quality is worse
                elif rating_diff_pct < 0:
                    comparison += f"but quality ratings would be {abs(rating_diff_pct):.1f}% lower.\n"
                # .. but quality is similar
                else:
                    comparison += f"with similar quality ratings."
            # if no price savings but..
            else:
                comparison += f"you would pay £{abs(price_savings):.2f} more "

                # .. quality is better
                if rating_diff_pct > 0:
                    comparison += f"but have {rating_diff_pct:.1f}% better quality (based on ratings), which outweighs the price difference according to your preferences."
                # .. quality is similar
                else:
                    comparison += f"with similar quality ratings, but other factors in your preferences make this the better overall choice."

            recommendation += comparison

        return recommendation

    def generate_outliers_recommendation (self, df):

        outliers_df= df[df['price_outliers']]

        if outliers_df.empty:
            return ""

        outlier_recommendation = f"\nThe following outliers were detected in your basket and may be effecting your recommendation:"

        for shop in outliers_df['shop_name'].unique():
            shop_outlier = outliers_df[outliers_df['shop_name'] == shop]
            outlier_recommendation += f"\n\nShop: {shop}"
            for _, row in shop_outlier.iterrows():
                price_type = "High price outlier" if row['price_zscore'] > 0 else "Low price outlier"
                outlier_recommendation += f"\n{row['product_name']}: £{row['price']:.2f} ({price_type})"

        return outlier_recommendation


    def export_excel(self, final_table, wsm_scores, basket_id, user_id, output_dir="."):

        # export the final table
        final_table.to_excel(f"{output_dir}/basket_{basket_id}_analysis.xlsx")

        # export the wsm scores
        wsm_scores.to_excel(f"{output_dir}/basket_{basket_id}_user_{user_id}_wsm_scores.xlsx", index=False)
        return True