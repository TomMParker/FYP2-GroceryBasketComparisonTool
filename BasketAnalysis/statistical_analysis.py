import pandas as pd
from scipy.stats import friedmanchisquare, rankdata
import numpy as np
import pingouin as pg


class StatisticalAnalysis:

    def calculate_z_scores(self, df):
        # copy data frame and calc zscores
        df_copy = df.copy()
        df_copy['price_zscore'] = df_copy.groupby('product_id')['price'].transform(
            lambda x: (x - x.mean()) / x.std() if x.std() != 0 else 0 # if: prevent /0 error
        )
        return df_copy



    # find items that z-score is
    def calculate_z_score_outliers(self, df, threshold=1.5):

        df_copy = df.copy()

        # mark as outlier is absolute z-score is greater than threshold
        df_copy['price_outliers'] = df_copy['price_zscore'].abs() > threshold
        return df_copy

    # no longer needed, used in early version of Friedman test, check for other uses and delete
    #def rank_prices(self, df):
    #   df_copy = df.copy()
    #   df_copy['rank'] = df_copy.groupby('product_id')['price'].transform(
    #     lambda x: rankdata(x, method='average')
    #)
        #return df_copy

    #def calculate_rank_sums(self, df):
    #   return df.groupby('shop_name')['rank'].sum().reset_index()

    def perform_friedman_test_on_price(self, df):
        # get prices for each product across shops
        pivot_df = df.pivot_table(
            index='product_id',
            columns='shop_name',
            values='price'
        )

        #rank shops, lower prices = higher rank
        ranked_df = pivot_df.rank(axis=1, method='average', ascending=True)

        # get shop names from pivot columns
        shops = ranked_df.columns.tolist()

        # prepare data for Friedman test
        shop_data = [ranked_df[shop] for shop in shops]

        # perform test
        try:
            stat, p = friedmanchisquare(*shop_data, nan_policy='omit')
            return stat, p
        except Exception as e:
            print("Error in test")
            return None, None

    def perform_friedman_test_on_ratings(self, df):
        # get ratings for each product across shops
        pivot_df = df.pivot_table(
            index='product_id',
            columns='shop_name',
            values='rating'
        )

        # rank shops, higher rating = higher rank
        ranked_df = pivot_df.rank(axis=1, method='average', ascending=False)

        # get shop names from pivot columns
        shops = ranked_df.columns.tolist()

        # prepare data for Friedman test
        shop_data = [ranked_df[shop] for shop in shops]

        # perform test
        try:
            stat, p = friedmanchisquare(*shop_data, nan_policy='omit')
            return stat, p
        except Exception as e:
            print("Error in test")
            return None, None
