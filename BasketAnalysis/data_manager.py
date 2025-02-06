from sqlalchemy import create_engine
import pandas as pd


class DataManager:
    def __init__(self, connection_string=None):
        if connection_string is None:
            self.connection_string = (
                "mysql+mysqlconnector://tp558_Products:r}FxB.u8J^d2dr2@"
                "brighton.reclaimhosting.com/tp558_SupermarketPrices"
            )
        else:
            self.connection_string = connection_string

        self.engine = None

    # db connect/disconnect
    def connect(self):

        self.engine = create_engine(self.connection_string)
        return self.engine

    def disconnect(self):
        if self.engine:
            self.engine.dispose()

    def get_user_data(self, user_id):
        # get user weightings
        weighting_query = """
            SELECT price_weight, convenience_weight, quality_weight
            FROM UserWeightings
            WHERE user_id = %s
        """
        # add to weighting df
        weighting_df = pd.read_sql(weighting_query, self.engine, params=(user_id,))

        # get preferences
        preference_query = """
            SELECT asda_preference, aldi_preference, sainsburys_preference, tesco_preference
            FROM Users
            WHERE user_id = %s
        """
        # add to preferences df
        preference_df = pd.read_sql(preference_query, self.engine, params=(user_id,))

        return weighting_df.iloc[0], preference_df.iloc[0]

    def get_basket_data(self, basket_id):
        # get basket items and prices from each shop
        query = """
            SELECT 
                bi.product_id, 
                p.product_name, 
                pp.shop_id, 
                s.shop_name, 
                pp.price, 
                pp.rating
            FROM BasketItems bi
            JOIN Products p ON bi.product_id = p.product_id
            JOIN ProductPrices pp ON bi.product_id = pp.product_id
            JOIN Shops s ON pp.shop_id = s.shop_id
            WHERE bi.basket_id = %s
        """
        #add to dataframe
        df = pd.read_sql(query, self.engine, params=(basket_id,))
        return df