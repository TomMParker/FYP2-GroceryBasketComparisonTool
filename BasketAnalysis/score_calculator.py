from sys import prefix

import pandas as pd
from statsmodels.tsa.statespace.tools import prefix_sv_map, prefix_pacf_map


class ScoreCalculator:

    def calculate_convenience_scores(self, preferences):

        #convert preferences to a score between 0.25 & 1
        pref_scores = {
            'Asda': 1.0 / preferences['asda_preference'],
            'Aldi': 1.0 / preferences['aldi_preference'],
            'Sainsburys': 1.0 / preferences['sainsburys_preference'],
            'Tesco': 1.0 / preferences['tesco_preference'],
        }

        return pref_scores



    def normalise_data(self, df):

        # normalise price and rating data
        df_copy = df.copy()

        # for each product group
        for product_id, group in df_copy.groupby('product_id'):
            # normalise price - lower better
            price_range = group['price'].max() - group['price'].min()
            if price_range > 0:
                df_copy.loc[group.index, 'normalised_price'] = (
                        (group['price'].max() - group['price']) / price_range
                )
            else:
                df_copy.loc[group.index, 'normalised_price'] = 1.0  # **check

            # normalise rating higher better
            rating_range = group['rating'].max() - group['rating'].min()
            if rating_range > 0:
                df_copy.loc[group.index, 'normalised_rating'] = (
                        (group['rating'] - group['rating'].min()) / rating_range
                )
            else:
                df_copy.loc[group.index, 'normalised_rating'] = 1.0  # all ratings equal

        return df_copy

    def calculate_wsm_scores(self, df, weights, convenience_scores):
        # group by shop and calculate average normalised values ** consider changing to sum
        wsm_scores = df.groupby('shop_name').agg(
            normalised_price=('normalised_price', 'sum'),
            normalised_rating=('normalised_rating', 'sum')
        ).reset_index()

        # add convenience scores
        wsm_scores['convenience_score'] = wsm_scores['shop_name'].map(convenience_scores)

        max_price_sum = wsm_scores['normalised_price'].max()
        max_rating_sum = wsm_scores['normalised_rating'].max()

        # rescale each to 0-1 by dividing by the max. needs to be if: to avoid /0 error from testing
        if max_price_sum > 0:
            wsm_scores['normalised_price'] = wsm_scores['normalised_price'] / max_price_sum
        if max_rating_sum > 0:
            wsm_scores['normalised_rating'] = wsm_scores['normalised_rating'] / max_price_sum

        # calculate WSM scores
        wsm_scores['wsm_score'] = (
                weights['price_weight'] * wsm_scores['normalised_price'] +
                weights['quality_weight'] * wsm_scores['normalised_rating'] +
                weights['convenience_weight'] * wsm_scores['convenience_score']
        )

        # rank shops based on WSM scores - higher bette
        wsm_scores['rank'] = wsm_scores['wsm_score'].rank(ascending=False)
        return wsm_scores