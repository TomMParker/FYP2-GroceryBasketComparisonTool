import pandas as pd

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

    # def generate_recommendation(self, wsm_scores):
    #     if wsm_scores.empty:
    #         return "Not enough data to make a recommendation."
    #
    #     best_shop = wsm_scores.loc[wsm_scores['wsm_score'].idxmax(), 'shop_name']
    #     return f"Considering your preferences, the best shop for you to buy your goods at is: {best_shop}"

    # generates recommendation basend on wsm scores, user weights and statistical analysis
    # threshold arg determines what level a weighting is deemed important
    def generate_enhanced_recommendation(self, wsm_scores, weights, preferences, price_friedman, rating_friedman, df, threshold=0.33):

        if wsm_scores.empty:
            return "Not enough data to make a recommendation."

        best_shop = wsm_scores.loc[wsm_scores['wsm_score'].idxmax(), 'shop_name']

        # check price differences between cheapest and most expensive stores
        store_totals = df.groupby('shop_name')['price'].sum().reset_index()
        cheapest_store = store_totals.loc[store_totals['price'].idxmin(), 'shop_name']
        cheapest_price = store_totals['price'].min()
        most_expensive_price = store_totals['price'].max()
        price_difference = most_expensive_price - cheapest_price
        percent_difference = (price_difference / cheapest_price) * 100
        significant_price_diff = price_difference > 5.0

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
                recommendation += "Statistical analysis confirms that both price and quality differences between shops are significant. " \
                                  "Your balanced preference for these factors aligns well with the observed differences between shops.\n\n"

            # .. price significant but not ratings
            elif price_significant and not rating_significant:
                recommendation += "Statistical analysis shows that price differences between shops are significant, but quality ratings are not. " \
                                  "Your preference for both factors is balanced, so you might want to consider increasing your price weighting.\n\n"
            # .. price not significant but ratings are
            elif not price_significant and rating_significant:
                recommendation += "Statistical analysis shows that quality differences between shops are significant, but price differences are not. " \
                                  "Your preference for both factors is balanced, so you might want to consider increasing your quality weighting.\n\n"
            # .. neither significant
            else:
                recommendation += "Statistical analysis shows that neither price nor quality differences between shops are significant. " \
                                  "Any shop would provide similar value based on your preferences.\n\n"

        # user care mainly about price:
        elif price_important and not quality_important:
            if price_significant:
                recommendation += "Statistical analysis confirms that price differences between shops are significant. " \
                                  "Your focus on price aligns well with the observed differences between shops.\n\n"
            else:
                recommendation += "Statistical analysis shows that price differences between shops are not statistically significant. " \
                                  "Since price is important to you, be aware that your chosen shop offers similar value to others in terms of pricing.\n\n"

        # user care mainly about quality:
        elif quality_important and not price_important:
            if rating_significant:
                recommendation += "Statistical analysis confirms that quality differences between shops are significant. " \
                                  "Your focus on quality aligns well with the observed differences between shops.\n\n"
            else:
                recommendation += "Statistical analysis shows that quality differences between shops are not statistically significant. " \
                                  "Since quality is important to you, be aware that your chosen shop offers similar value to others in terms of quality.\n\n"

        else:
            # user cares mainly convenience over price and quality:
            if convenience_important:
                recommendation += "Based on your preferences, convenience appears to be your primary concern.\n\n"
            else:
                recommendation += "Your preferences don't show a strong weighting toward any specific factor. " \
                                  "Consider adjusting your weightings to better reflect what's important to you.\n\n"

        # main shop recommendation
        recommendation += f"Considering your preferences for {preference_str}, the best shop for you to buy your goods at is: {best_shop}\n\n"

        # if best_shop is not same as preferred shop add savings and ratings diff
        recommendation = self._add_preferred_shop_comparison(recommendation, df, wsm_scores, preferences, best_shop)

        return recommendation

    # adds comparison between preferred shop and best_shop if different
    def _add_preferred_shop_comparison(self, recommendation, df, wsm_scores, preferences, best_shop):

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

            comparison = f"Your preferred shop is {preferred_shop}, however if you were to switch to {best_shop} "

            # if there are price savings..
            if price_savings > 0:
                comparison += f"you would save £{price_savings:.2f} "

                # .. and quality is better
                if rating_diff_pct > 0:
                    comparison += f"and have an improvement in quality (based on ratings) of {rating_diff_pct:.1f}%."
                # .. but quality is worse
                elif rating_diff_pct < 0:
                    comparison += f"but quality ratings would be {abs(rating_diff_pct):.1f}% lower."
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


    def export_excel(self, final_table, wsm_scores, basket_id, user_id, output_dir="."):

        # export the final table
        final_table.to_excel(f"{output_dir}/basket_{basket_id}_analysis.xlsx")

        # export the wsm scores
        wsm_scores.to_excel(f"{output_dir}/basket_{basket_id}_user_{user_id}_wsm_scores.xlsx", index=False)
        return True