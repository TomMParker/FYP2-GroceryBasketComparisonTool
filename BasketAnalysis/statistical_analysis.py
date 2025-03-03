import pandas as pd
from scipy.stats import friedmanchisquare, rankdata


class StatisticalAnalysis:

    def calculate_z_scores(self, df):
        # copy data frame and calc zscores
        df_copy = df.copy()
        df_copy['price_zscore'] = df_copy.groupby('product_id')['price'].transform(
            lambda x: (x - x.mean()) / x.std()
        )
        return df_copy


    # find items that z-score is
    def calculate_z_score_outliers(self, df, threshold=1.5):

        df_copy = df.copy()

        # mark as outlier is absolute z-score is greater than threshold
        df_copy['price_outliers'] = df_copy['price_zscore'].abs() > threshold
        return df_copy

    def rank_prices(self, df):
        df_copy = df.copy()
        df_copy['rank'] = df_copy.groupby('product_id')['price'].transform(
            lambda x: rankdata(x, method='average')
        )
        return df_copy

    def calculate_rank_sums(self, df):
        return df.groupby('shop_name')['rank'].sum().reset_index()

    def perform_friedman_test_on_price(self, df):
        # get prices for each product across shops
        pivot_df = df.pivot_table(
            index='product_id',
            columns='shop_name',
            values='price'
        )

        # get shop names from pivot columns
        shops = pivot_df.columns.tolist()


        # prepare data for Friedman test
        shop_data = [pivot_df[shop].dropna() for shop in shops]

        # perform test
        if all(len(data) > 0 for data in shop_data):
            stat, p_value = friedmanchisquare(*shop_data)
            return stat, p_value
        else:
            return None, None

    def perform_friedman_test_on_ratings(self, df):
        # get ratings for each product across shops
        pivot_df = df.pivot_table(
            index='product_id',
            columns='shop_name',
            values='rating'
        )


        #tidy this??
        # get shop names from pivot columns
        shops = pivot_df.columns.tolist()


        # prepare data for Friedman test
        shop_data = [pivot_df[shop].dropna() for shop in shops]

        # perform test
        if all(len(data) > 0 for data in shop_data):
            stat, p_value = friedmanchisquare(*shop_data)
            return stat, p_value
        else:
            return None, None