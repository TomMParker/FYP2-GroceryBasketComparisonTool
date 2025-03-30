from data_manager import DataManager
from statistical_analysis import StatisticalAnalysis
from score_calculator import ScoreCalculator
from report_generator import ReportGenerator
from visualisation import VisualisationManager


class BasketAnalysis:
    def __init__(self, connection_string=None):
        self.data_manager = DataManager(connection_string)
        self.statistical_analysis = StatisticalAnalysis()
        self.score_calculator = ScoreCalculator()
        self.report_generator = ReportGenerator()
        self.visualisation_manager = VisualisationManager()

    # analyse basket and generate recommendation
    def analyse_basket(self, basket_id, user_id, output_dir="."):
        # connect to database
        self.data_manager.connect()

        try:
            # 1: get user data
            weights, preferences = self.data_manager.get_user_data(user_id)

            # 2: calculate convenience scores
            convenience_scores = self.score_calculator.calculate_convenience_scores(preferences)

            # 3: get basket data
            df = self.data_manager.get_basket_data(basket_id)
            df.to_excel(f"./dataframe_tests/basket_{basket_id}_01_raw_data.xlsx")

            # skip analysis if no data
            #if df.empty:
            #    return None, None, None, None, None, None, "No data found for this basket."

            # 4: calculate Z-scores
            df = self.statistical_analysis.calculate_z_scores(df)
            df.to_excel(f"./dataframe_tests/basket_{basket_id}_02_with_zscores.xlsx")

            # 4b: calsulate z-score outliers
            df = self.statistical_analysis.calculate_z_score_outliers(df, threshold=1.5)
            df.to_excel(f"./dataframe_tests/basket_{basket_id}_03_with_outliers.xlsx")

            # 5: rank prices
            df = self.statistical_analysis.rank_prices(df)
            df.to_excel(f"./dataframe_tests/basket_{basket_id}_04_with_ranks.xlsx")

            # 6: calculate rank sums
            rank_sums = self.statistical_analysis.calculate_rank_sums(df)
            rank_sums.to_excel(f"./dataframe_tests/basket_{basket_id}_05_rank_sums.xlsx")

            # 7: friedman test on prices
            friedman_stat, friedman_p_value = self.statistical_analysis.perform_friedman_test_on_price(df)

            # 7b: friedman test on ratings
            rating_friedman_stat, rating_friedman_p_value = self.statistical_analysis.perform_friedman_test_on_ratings(df)

            # 8: normalise data for WSM
            df = self.score_calculator.normalise_data(df)
            df.to_excel(f"./dataframe_tests/basket_{basket_id}_06_normalised_data.xlsx")

            # 9: calculate WSM scores
            wsm_scores = self.score_calculator.calculate_wsm_scores(df, weights, convenience_scores)
            wsm_scores.to_excel(f"./dataframe_tests/basket_{basket_id}_07_wsm_scores.xlsx")

            # 10: create final table
            final_table = self.report_generator.create_final_table(df)

            # 11: generate recommendation
            recommendation = self.report_generator.generate_enhanced_recommendation(
                wsm_scores,
                weights,
                preferences,
                (friedman_stat, friedman_p_value),
                (rating_friedman_stat, rating_friedman_p_value),
                df  # pass the dataframe
            )

            # 12: egnerate horizontal box plot for all products
            #boxplot_file = self.visualization_manager.generate_horizontal_boxplot(df, output_dir)

            # 13: create simple Excel with the box plot only
            #price_analysis_file = self.visualization_manager.create_excel_with_boxplot(boxplot_file, basket_id, output_dir)

            # 12: export results
            self.report_generator.export_excel(final_table, wsm_scores, basket_id, user_id, "report_exports")



            return (df, final_table, friedman_stat, friedman_p_value, rating_friedman_stat,
                    rating_friedman_p_value, rank_sums, wsm_scores, recommendation)

        finally:
            # 14: disconnect from database
            self.data_manager.disconnect()


# test run
if __name__ == "__main__":
    analyser = BasketAnalysis()
    basket_id = 15
    user_id = 1

    df, final_table, friedman_stat, friedman_p_value, rating_friedman_stat, rating_friedman_p_value, rank_sums, wsm_scores, recommendation = analyser.analyse_basket(basket_id, user_id)

    # print basket details
    print("=" * 100)
    print("BASKET ANALYSIS RESULTS")
    print("=" * 100)

    print("\nBasket Items and Prices:")
    print("-" * 50)
    print(df[['product_name', 'shop_name', 'price', 'rating']].sort_values('product_name'))

    # print Z-score outliers
    outliers_df = df[df['price_outliers']]
    print("\nPrice Outliers (Z-score > 1.5):")
    print("-" * 50)
    if not outliers_df.empty:
        print(outliers_df[['product_name', 'shop_name', 'price', 'price_zscore']])
    else:
        print("No significant price outliers detected.")

    # print rank sums (sorted by rank)
    print("\nPrice Rank Sums (lower is better):")
    print("-" * 50)
    print(rank_sums.sort_values('rank'))

    # print WSM scores (sorted by score, descending)
    print("\nWeighted Sum Model Scores:")
    print("-" * 50)
    print(wsm_scores.sort_values('wsm_score', ascending=False))

    # print friedman test results for prices
    print("\nFriedman Test Results (Prices):")
    print("-" * 40)
    if friedman_stat is not None:
        print(f"Statistic: {friedman_stat:.4f}")
        print(f"p-value: {friedman_p_value:.4f}")
        print(f"Significant difference: {'Yes' if friedman_p_value < 0.05 else 'No'}")
    else:
        print("Not enough data to perform Friedman test on prices")

    # print friedman test results for ratings
    print("\nFriedman Test Results (Ratings):")
    print("-" * 50)
    if rating_friedman_stat is not None:
        print(f"Statistic: {rating_friedman_stat:.4f}")
        print(f"p-value: {rating_friedman_p_value:.4f}")
        print(f"Significant difference: {'Yes' if rating_friedman_p_value < 0.05 else 'No'}")
    else:
        print("Not enough data to perform Friedman test on ratings")

    # print the cheapest store
    cheapest_store = rank_sums.iloc[rank_sums['rank'].argmin()]['shop_name']

    # print the highest rated store
    rating_by_shop = df.groupby('shop_name')['rating'].mean().reset_index()
    highest_rated_store = rating_by_shop.loc[rating_by_shop['rating'].idxmax(), 'shop_name']

    # print the most convenient store (from the WSM scores)
    most_convenient = wsm_scores.iloc[wsm_scores['convenience_score'].argmax()]['shop_name']

    print("\nTotal Cost:")
    print("-" * 40)
    store_totals = df.groupby('shop_name')['price'].sum().reset_index()
    for _, row in store_totals.sort_values('price').iterrows():
        print(f"{row['shop_name']}: £{row['price']:.2f}")

    print("\nStore Rankings:")
    print("-" * 40)
    print(f"Cheapest Store: {cheapest_store}")
    print(f"Highest Rated Store: {highest_rated_store}")
    print(f"Most Convenient Store: {most_convenient}")

    # print final recommendation
    print("\nRECOMMENDATION:")
    print("=" * 80)
    print(recommendation)