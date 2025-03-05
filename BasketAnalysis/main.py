from data_manager import DataManager
from statistical_analysis import StatisticalAnalysis
from score_calculator import ScoreCalculator
from report_generator import ReportGenerator

class BasketAnalysis:
    def __init__(self, connection_string=None):
        self.data_manager = DataManager(connection_string)
        self.statistical_analysis = StatisticalAnalysis()
        self.score_calculator = ScoreCalculator()
        self.report_generator = ReportGenerator()

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

            # skip analysis if no data
            if df.empty:
                return None, None, None, None, None, None, "No data found for this basket."

            # 4: calculate Z-scores
            df = self.statistical_analysis.calculate_z_scores(df)

            df = self.statistical_analysis.calculate_z_score_outliers(df, threshold=1.1)

            outliers_df = df[df['is_price_outlier']]
            if not outliers_df.empty:
                print("Price outliers detected:")
                print(outliers_df[['product_name', 'shop_name', 'price', 'price_zscore']])

            # 5: rank prices
            df = self.statistical_analysis.rank_prices(df)

            # 6: calculate rank sums
            rank_sums = self.statistical_analysis.calculate_rank_sums(df)

            # 7: perform Friedman Test
            friedman_stat, friedman_p_value = self.statistical_analysis.perform_friedman_test_on_price(df)

            # 8: normalise data for WSM
            df = self.score_calculator.normalise_data(df)

            # 9: calculate WSM scores
            wsm_scores = self.score_calculator.calculate_wsm_scores(df, weights, convenience_scores)

            # 10: create final table
            final_table = self.report_generator.create_final_table(df)

            # 11: generate recommendation
            recommendation = self.report_generator.generate_recommendation(wsm_scores)

            # 12: export results
            self.report_generator.export_excel(final_table, wsm_scores, basket_id, output_dir)

            return df, final_table, friedman_stat, friedman_p_value, rank_sums, wsm_scores, recommendation

        finally:
            # disconnect from database
            self.data_manager.disconnect()


# test
if __name__ == "__main__":
    analyser = BasketAnalysis()
    basket_id = 10
    user_id = 1

    df, final_table, friedman_stat, friedman_p_value, rank_sums, wsm_scores, recommendation = analyser.analyse_basket(
        basket_id, user_id)

    print("Final Table:")
    print(final_table)
    print("\nRank Sums:")
    print(rank_sums)
    print("\nWSM Scores:")
    print(wsm_scores)
    print("\nFriedman Test Results:")
    if friedman_stat is not None:
        print(f"Statistic: {friedman_stat}, p-value: {friedman_p_value}")
    else:
        print("Not enough data to perform Friedman test")

    print(f"\n{recommendation}")